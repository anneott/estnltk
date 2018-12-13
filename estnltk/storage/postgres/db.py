import os
import re
import json
import pandas
import operator as op
from contextlib import contextmanager
import collections
from functools import reduce
from itertools import chain

from tqdm import tqdm, tqdm_notebook

import psycopg2
from psycopg2.extensions import STATUS_BEGIN
from psycopg2.sql import SQL, Identifier, Literal, DEFAULT, Composed

from estnltk import logger
from estnltk.converters.dict_importer import dict_to_layer
from estnltk.converters.dict_exporter import layer_to_dict
from estnltk.converters import dict_to_text, text_to_json
from estnltk.layer_operations import create_ngram_fingerprint_index
from .query import Query


class PgStorageException(Exception):
    pass


class PgCollectionException(Exception):
    pass


RowMapperRecord = collections.namedtuple("RowMapperRecord", ["layer", "meta"])

pytype2dbtype = {
    "int": "integer",
    "bigint": "bigint",
    "float": "double precision",
    "str": "text"
}


def get_query_length(q):
    """:returns
    approximate number of characters in the psycopg2 SQL query
    """
    result = 0
    if isinstance(q, Composed):
        for r in q:
            result += get_query_length(r)
    elif isinstance(q, (SQL, Identifier)):
        result += len(q.string)
    else:
        result += len(str(q.wrapped))
    return result


class PgCollection:
    """Convenience wrapper over PostgresStorage"""

    def __init__(self, name, storage, meta=None, temporary=False):
        if '__' in name:
            raise PgCollectionException('collection name must not contain double underscore: {!r}'.format(name))
        self.table_name = name
        self.storage = storage
        # TODO: read meta columns from collection table if exists, move this parameter to self.create
        self.meta = meta or {}
        self._temporary = temporary
        self._structure = self._get_structure()
        self.column_names = ['id', 'data'] + list(self.meta)

        self._buffered_insert_query_length = 0

    def create(self, description=None):
        """Creates the database tables for the collection"""
        temporary = SQL('TEMPORARY') if self._temporary else SQL('')
        with self.storage.conn.cursor() as c:
            c.execute(SQL('CREATE {temporary} TABLE {structure} ('
                          'layer_name text primary key, '
                          'detached bool not null, '
                          'attributes text[] not null, '
                          'ambiguous bool not null, '
                          'parent text, '
                          'enveloping text, '
                          '_base text, '
                          'meta text[]);').format(temporary=temporary,
                                                  structure=self._structure_identifier()))
            logger.info('new empty collection {!r} created'.format(self.table_name))
            logger.debug(c.query.decode())

        return self.storage.create_table(table=self.table_name,
                                         description=description,
                                         meta=self.meta,
                                         temporary=self._temporary,
                                         table_identifier=self._collection_identifier())

    def create_index(self):
        """create index for the collection table"""
        with self.storage.conn.cursor() as c:
            c.execute(
                SQL("CREATE INDEX {index} ON {table} USING gin ((data->'layers') jsonb_path_ops)").format(
                    index=Identifier('idx_%s_data' % self.table_name),
                    table=self._collection_identifier()))

    def drop_index(self):
        """drop index of the collection table"""
        with self.storage.conn.cursor() as c:
            c.execute(
                SQL("DROP INDEX {schema}.{index}").format(
                    schema=Identifier(self.storage.schema),
                    index=Identifier('idx_%s_data' % self.table_name)))

    # TODO: make it work
    def extend(self, other: 'PgCollection'):
        if self.column_names != other.column_names:
            raise PgCollectionException("can't extend: different collection meta")
        if self._structure != other._structure:
            raise PgCollectionException("can't extend: structures are different")
        with self.storage.conn.cursor() as cursor:
            cursor.execute(SQL('INSERT INTO {} SELECT * FROM {}').format(self._collection_identifier(),
                                                                         other._collection_identifier()))
            for layer_name, struct in self._structure.items():
                if struct['detached']:
                    cursor.execute(SQL('INSERT INTO {} SELECT * FROM {}').format(self._layer_identifier(layer_name),
                                                                                 other._layer_identifier(layer_name)))

    def _get_structure(self):
        if not self.exists():
            return None
        structure = {}
        with self.storage.conn.cursor() as c:
            c.execute(SQL("SELECT layer_name, detached, attributes, ambiguous, parent, enveloping, _base, meta "
                          "FROM {};").format(self._structure_identifier()))

            for row in c.fetchall():
                structure[row[0]] = {'detached': row[1],
                                     'attributes': tuple(row[2]),
                                     'ambiguous': row[3],
                                     'parent': row[4],
                                     'enveloping': row[5],
                                     '_base': row[6],
                                     'meta': row[7]}
        return structure

    def _insert_into_structure(self, layer, detached: bool, meta: dict=None):
        meta = list(meta or [])
        with self.storage.conn.cursor() as c:
            c.execute(SQL("INSERT INTO {} (layer_name, detached, attributes, ambiguous, parent, enveloping, _base, meta) "
                          "VALUES ({}, {}, {}, {}, {}, {}, {}, {});").format(
                self._structure_identifier(),
                Literal(layer.name),
                Literal(detached),
                Literal(list(layer.attributes)),
                Literal(layer.ambiguous),
                Literal(layer.parent),
                Literal(layer.enveloping),
                Literal(layer._base),
                Literal(meta)
            )
            )
        self._structure = self._get_structure()

    def _delete_from_structure(self, layer_name):
        with self.storage.conn.cursor() as c:
            c.execute(SQL("DELETE FROM {} WHERE layer_name={};").format(
                self._structure_identifier(),
                Literal(layer_name)
            )
            )
            logger.debug(c.query.decode())
        self._structure = self._get_structure()

    def insert(self, text, key=None, meta_data=None):
        return self._buffered_insert(text=text, buffer=[], buffer_size=0, query_length_limit=0, key=key,
                                     meta_data=meta_data)

    # TODO: merge this with buffered_layer_insert
    @contextmanager
    def buffered_insert(self, buffer_size=10000, query_length_limit=5000000):
        buffer = []
        self._buffered_insert_query_length = 0

        def wrap_buffered_insert(text, key=None, meta_data=None):
            return self._buffered_insert(text, buffer=buffer, buffer_size=buffer_size,
                                         query_length_limit=query_length_limit, key=key, meta_data=meta_data)

        try:
            yield wrap_buffered_insert
        finally:
            self._flush_insert_buffer(buffer)

    def _buffered_insert(self, text, buffer, buffer_size, query_length_limit, key=None, meta_data=None):
        """Saves a given `Text` object into the collection.

        Args:
            text: Text
            key: int
            meta_data: dict
            buffer_size: int
                number of text objects to buffer before inserting into collection table
                run PgCollection.flush_buffer after last insert

        Returns:
            int: row key (id)
        """

        if self._structure is None:
            for layer in text.layers:
                self._insert_into_structure(text[layer], detached=False)
        elif any(struct['detached'] for struct in self._structure.values()):
            # TODO: solve this case in a better way
            raise PgCollectionException("this collection has detached layers, can't add new text objects")
        else:
            assert set(text.layers) == set(self._structure), '{} != {}'.format(set(text.layers), set(self._structure))
            for layer_name, layer in text.layers.items():
                layer_struct = self._structure[layer_name]
                assert layer_struct['detached'] is False
                assert layer_struct['attributes'] == layer.attributes, '{} != {}'.format(layer_struct['attributes'],
                                                                                         layer.attributes)
                assert layer_struct['ambiguous'] == layer.ambiguous
                assert layer_struct['parent'] == layer.parent
                assert layer_struct['enveloping'] == layer.enveloping
                assert layer_struct['_base'] == layer._base
        text = text_to_json(text)
        if key is None:
            key = DEFAULT
        else:
            key = Literal(key)

        row = [key, Literal(text)]
        for k in self.column_names[2:]:
            if k in meta_data:
                m = Literal(meta_data[k])
            else:
                m = DEFAULT
            row.append(m)

        q = SQL('({})').format(SQL(', ').join(row))
        self._buffered_insert_query_length += get_query_length(q)
        buffer.append(q)

        if len(buffer) >= buffer_size or self._buffered_insert_query_length >= query_length_limit:
            ids = self._flush_insert_buffer(buffer)
            self._buffered_insert_query_length = 0
            if buffer_size == 0 and len(ids) == 1:
                return ids[0]
            return ids

    def _flush_insert_buffer(self, buffer):
        if len(buffer) == 0:
            return []
        sql_column_names = SQL(', ').join(map(Identifier, self.column_names))
        with self.storage.conn.cursor() as c:
            c.execute(SQL('INSERT INTO {} ({}) VALUES {} RETURNING id;').format(
                self._collection_identifier(),
                sql_column_names,
                SQL(', ').join(buffer)))
            row_key = c.fetchone()
            logger.debug('flush buffer: {} rows, {} bytes, {} estimated characters'.format(len(buffer),
                                                                                           len(c.query),
                                                                                           self._buffered_insert_query_length))
        buffer.clear()
        return row_key

    @contextmanager
    def buffered_layer_insert(self, table_identifier, columns, buffer_size=10000, query_length_limit=5000000):
        """General context manager for buffered insert"""
        buffer = []
        column_identifiers = SQL(', ').join(map(Identifier, columns))

        self._buffered_insert_query_length = get_query_length(column_identifiers)

        with self.storage.conn.cursor() as cursor:
            def buffered_insert(values):
                q = SQL('({})').format(SQL(', ').join(values))
                buffer.append(q)
                self._buffered_insert_query_length += get_query_length(q)

                if len(buffer) >= buffer_size or self._buffered_insert_query_length >= query_length_limit:
                    return self._flush_layer_insert_buffer(cursor=cursor,
                                                           table_identifier=table_identifier,
                                                           column_identifiers=column_identifiers,
                                                           buffer=buffer)
            try:
                yield buffered_insert
            finally:
                self._flush_layer_insert_buffer(cursor=cursor,
                                                table_identifier=table_identifier,
                                                column_identifiers=column_identifiers,
                                                buffer=buffer)
                self.storage.conn.autocommit = False

    def _flush_layer_insert_buffer(self, cursor, table_identifier, column_identifiers, buffer):
        if len(buffer) == 0:
            return []

        cursor.execute(SQL('INSERT INTO {} ({}) VALUES {} RETURNING id;').format(
                        table_identifier,
                        column_identifiers,
                        SQL(', ').join(buffer)))
        row_key = cursor.fetchall()
        logger.debug('flush buffer: {} rows, {} bytes, {} estimated characters'.format(
                     len(buffer), len(cursor.query), self._buffered_insert_query_length))
        buffer.clear()
        self._buffered_insert_query_length = get_query_length(column_identifiers)
        return row_key

    def exists(self):
        """Returns true if collection tables exists"""
        collection_table_exists = self.storage.table_exists(self.table_name)
        structure_table_exists = self.storage.table_exists(self._structure_table_name())
        assert collection_table_exists is structure_table_exists, (collection_table_exists, structure_table_exists)
        return collection_table_exists

    def select_fragment_raw(self, fragment_name, parent_layer_name, query=None, ngram_query=None):
        return self.storage.select_fragment_raw(
            fragment_table=self.fragment_name_to_table_name(fragment_name),
            text_table=self.table_name,
            parent_layer_table=self.layer_name_to_table_name(parent_layer_name),
            query=query,
            ngram_query=ngram_query)

    def select_raw(self,
                   query=None,
                   layer_query: 'JsonbLayerQuery' = None,
                   layer_ngram_query: dict = None,
                   layers: list = None,
                   keys: list = None,
                   order_by_key: bool = False,
                   collection_meta: list = None,
                   missing_layer: str = None):
        """
        Select from collection table with possible search constraints.

        Args:
            table: str
                collection table
            query: JsonbTextQuery
                collection table query
            layer_query: JsonbLayerQuery
                layer query
            layer_ngram_query: dict
            keys: list
                List of id-s.
            order_by_key: bool
            layers: list
                Layers to fetch. Specified layers will be merged into returned text object and
                become accessible via `text["layer_name"]`.
            collection_meta: list
                list of collection metadata column names
            missing_layer: str
                name of the layer
                select collection objects for which there is no entry in the table `missing_layer`

        Returns:
            iterator of (key, text) pairs

        Example:

            q = JsonbTextQuery('morph_analysis', lemma='laulma')
            for key, txt in storage.select(table, query=q):
                print(key, txt)
        """
        table = self.table_name
        with self.storage.conn.cursor('read', withhold=True) as c:
            # 1. Build query

            where = False
            sql_parts = []
            collection_identifier = self._collection_identifier()
            table_escaped = SQL("{}").format(collection_identifier).as_string(self.storage.conn)
            collection_meta = collection_meta or []
            collection_columns = SQL(', ').join(SQL('{}.{}').format(collection_identifier, column_id) for
                                                column_id in map(Identifier, ['id', 'data', *collection_meta]))
            if not layers and layer_query is None and layer_ngram_query is None:
                # select only text table
                q = SQL("SELECT {} FROM {}").format(collection_columns, collection_identifier).as_string(self.storage.conn)
                sql_parts.append(q)
            else:
                # need to join text and all layer tables
                layers = layers or []
                layer_query = layer_query or {}
                layer_ngram_query = layer_ngram_query or {}

                layers_select = []
                for layer in chain(layers):
                    layer = SQL("{}").format(self._layer_identifier(layer)).as_string(self.storage.conn)
                    layers_select.append(layer)

                layers_join = set()
                for layer in chain(layers, layer_query.keys(), layer_ngram_query.keys()):
                    layer = SQL("{}").format(self._layer_identifier(layer)).as_string(self.storage.conn)
                    layers_join.add(layer)

                q = 'SELECT {collection_columns} {select} FROM {table}, {layers_join} WHERE {where}'.format(
                    collection_columns=collection_columns.as_string(self.storage.conn),
                    table=table_escaped,
                    select=", %s" % ", ".join(
                        "{0}.id, {0}.data".format(layer) for layer in layers_select) if layers_select else "",
                    layers_join=", ".join(layer for layer in layers_join),
                    where=" AND ".join("%s.id = %s.text_id" % (table_escaped, layer) for layer in layers_join))
                sql_parts.append(q)
                where = True

            if query is not None:
                # build constraint on the main text table
                sql_parts.append("%s %s" % ("AND" if where else "WHERE", query.eval()))
                where = True
            if layer_query:
                # build constraint on related layer tables
                q = " AND ".join(query.eval() for layer, query in layer_query.items())
                sql_parts.append("%s %s" % ("AND" if where else "WHERE", q))
                where = True
            if keys is None:
                keys = []
            else:
                keys = list(map(int, keys))
                # build constraint on id-s
                sql_parts.append("AND" if where else "WHERE")
                sql_parts.append("{table}.id = ANY(%(keys)s)".format(table=table_escaped))
                where = True
            if layer_ngram_query:
                # build constraint on related layer's ngram index
                q = self.storage.build_layer_ngram_query(layer_ngram_query, table)
                if where is True:
                    q = "AND %s" % q
                sql_parts.append(q)
                where = True
            if missing_layer:
                # select collection objects for which there is no entry in the layer table
                sql_parts.append("AND" if where else "WHERE")
                q = SQL('id NOT IN (SELECT text_id FROM {})').format(self._layer_identifier(missing_layer)).as_string(self.storage.conn)
                sql_parts.append(q)
                where = True

            if order_by_key is True:
                sql_parts.append("order by id")

            sql = " ".join(sql_parts)  # bad, bad string concatenation, but we can't avoid it here, right?

            # 2. Execute query
            c.execute(sql, {'keys': keys})
            logger.debug(c.query.decode())
            for row in c:
                text_id = row[0]
                text_dict = row[1]
                text = dict_to_text(text_dict)
                meta = row[2:2+len(collection_meta)]
                detached_layers = {}
                if len(row) > 2 + len(collection_meta):
                    for i in range(2 + len(collection_meta), len(row), 2):
                        layer_dict = row[i + 1]
                        layer = dict_to_layer(layer_dict, text, detached_layers)
                        detached_layers[layer.name] = layer
                result = text_id, text, meta, detached_layers
                yield result
        c.close()

    def _select(self, query=None, layer_query=None, layer_ngram_query=None, layers=None, keys=None,
                order_by_key=False, collection_meta=None, missing_layer: str = None):
        for row in self.select_raw(query=query,
                                   layer_query=layer_query,
                                   layer_ngram_query=layer_ngram_query,
                                   layers=layers,
                                   keys=keys,
                                   order_by_key=order_by_key,
                                   collection_meta=collection_meta,
                                   missing_layer=missing_layer):
            text_id, text, meta_list, detached_layers = row
            for layer_name in layers:
                text[layer_name] = detached_layers[layer_name]
            if collection_meta:
                meta = {}
                for meta_name, meta_value in zip(collection_meta, meta_list):
                    meta[meta_name] = meta_value
                yield text_id, text, meta
            else:
                yield text_id, text

    def select(self, query=None, layer_query=None, layer_ngram_query=None, layers=None, keys=None, order_by_key=False,
               collection_meta=None, progressbar=None, missing_layer: str = None):
        """See select_raw()"""
        if not self.exists():
            return
        layers_extended = []

        def include_dep(layer):
            if layer is None or not self._structure[layer]['detached']:
                return
            for dep in (self._structure[layer]['parent'], self._structure[layer]['enveloping']):
                include_dep(dep)
            if layer not in layers_extended:
                layers_extended.append(layer)

        for layer in layers or []:
            if layer not in self._structure:
                raise PgCollectionException('there is no {!r} layer in the collection {!r}'.format(
                        layer, self.table_name))
            include_dep(layer)

        data_iterator = self._select(query=query, layer_query=layer_query, layer_ngram_query=layer_ngram_query,
                                     layers=layers_extended, keys=keys, order_by_key=order_by_key,
                                     collection_meta=collection_meta, missing_layer=missing_layer)
        if progressbar not in {'ascii', 'unicode', 'notebook'}:
            yield from data_iterator
            return

        total = self.storage.count_rows(self.table_name)
        initial = 0
        if missing_layer is not None:
            initial = self.storage.count_rows(table_identifier=self._layer_identifier(missing_layer))
        if progressbar == 'notebook':
            iter_data = tqdm_notebook(data_iterator,
                                      total=total,
                                      initial=initial,
                                      unit='doc',
                                      smoothing=0)
        else:
            iter_data = tqdm(data_iterator,
                             total=total,
                             initial=initial,
                             unit='doc',
                             ascii=(progressbar == 'ascii'),
                             smoothing=0)
        for data in iter_data:
            iter_data.set_description('collection_id: {}'.format(data[0]), refresh=False)
            yield data

    def select_by_key(self, key, return_as_dict=False):
        """See PostgresStorage.select_by_key()"""
        return self.storage.select_by_key(self.table_name, key, return_as_dict)

    def count_values(self, layer, attr, **kwargs):
        """Count attribute values in the collection."""
        counter = collections.Counter()
        for i, t in self.select(layers=[layer], **kwargs):
            counter.update(t[layer].count_values(attr))
        return counter

    def find_fingerprint(self, query=None, layer_query=None, layer_ngram_query=None, layers=None, order_by_key=False):
        """See PostgresStorage.find_fingerprint()"""
        return self.storage.find_fingerprint(self.table_name, query, layer_query, layer_ngram_query, layers,
                                             order_by_key)

    def layer_name_to_table_name(self, layer_name):
        return self.storage.layer_name_to_table_name(self.table_name, layer_name)

    def _collection_identifier(self):
        if self._temporary:
            return Identifier(self.table_name)
        return SQL('{}.{}').format(Identifier(self.storage.schema), Identifier(self.table_name))

    def _structure_table_name(self):
        return self.table_name + '__structure'

    def _structure_identifier(self):
        if self._temporary:
            return Identifier(self._structure_table_name())
        return SQL('{}.{}').format(Identifier(self.storage.schema), Identifier(self._structure_table_name()))

    def _layer_identifier(self, layer_name):
        table_identifier = Identifier('{}__{}__layer'.format(self.table_name, layer_name))
        if self._temporary:
            return table_identifier
        return SQL('{}.{}').format(Identifier(self.storage.schema), table_identifier)

    def _fragment_identifier(self, fragment_name):
        if self._temporary:
            return Identifier('{}__{}__fragment'.format(self.table_name, fragment_name))
        return SQL('{}.{}').format(Identifier(self.storage.schema),
                                   Identifier('{}__{}__fragment'.format(self.table_name, fragment_name)))

    def fragment_name_to_table_name(self, fragment_name):
        return self.storage.fragment_name_to_table_name(self.table_name, fragment_name)

    def create_fragment(self, fragment_name, data_iterator, row_mapper,
                        create_index=False, ngram_index=None):
        """
        Creates and fills a fragment table.

        Args:
            fragment_name: str
            data_iterator: iterator
                Produces tuples (text_id, text, parent_layer_id, *payload),
                where *payload is a variable number of values to be passed to the `row_mapper`
                See method `PgCollection.select_raw`
            row_mapper: callable
                It takes as input a full row produced by `data_iterator`
                and returns a list of Layer objects.
            create_index:
            ngram_index:

        """
        conn = self.storage.conn
        with conn.cursor() as c:
            try:
                conn.autocommit = False
                # create fragment table and indices
                self.create_fragment_table(c, fragment_name,
                                           create_index=create_index,
                                           ngram_index=ngram_index)
                # insert data
                fragment_table = self.fragment_name_to_table_name(fragment_name)
                id_ = 0
                for row in data_iterator:
                    text_id, text, parent_layer_id = row[0], row[1], row[2]
                    for record in row_mapper(row):
                        fragment_dict = layer_to_dict(record.layer, text)
                        if ngram_index is not None:
                            ngram_values = [create_ngram_fingerprint_index(record.layer, attr, n)
                                            for attr, n in ngram_index.items()]
                        else:
                            ngram_values = None
                        layer_json = json.dumps(fragment_dict, ensure_ascii=False)
                        ngram_values = ngram_values or []
                        q = "INSERT INTO {}.{} VALUES (%s);" % ", ".join(['%s'] * (4 + len(ngram_values)))
                        q = SQL(q).format(Identifier(self.storage.schema), Identifier(fragment_table))
                        c.execute(q, (id_, parent_layer_id, text_id, layer_json, *ngram_values))
                        id_ += 1
            except:
                conn.rollback()
                raise
            finally:
                if conn.status == STATUS_BEGIN:
                    # no exception, transaction in progress
                    conn.commit()
                conn.autocommit = True

    def create_layer(self, layer_name=None, data_iterator=None, row_mapper=None, tagger=None,
                     create_index=False, ngram_index=None, overwrite=False, meta=None, progressbar=None):
        """
        Creates layer

        Args:
            layer_name:
            data_iterator: iterator
                Iterator over Text collection which generates tuples (`text_id`, `text`).
                See method `PgCollection.select`.
            row_mapper: function
                For each record produced by `data_iterator` return a list
                of `RowMapperRecord` objects.
            tagger: Tagger
                either tagger must be None or layer_name, data_iterator and row_mapper must be None
            create_index: bool
                Whether to create an index on json column
            ngram_index: list
                A list of attributes for which to create an ngram index
            overwrite: bool
                If True and layer table exists, table is overwritten.
                If False and layer table exists, error is raised.
            meta: dict of str -> str
                Specifies table column names and data types to create for storing additional
                meta information. E.g. meta={"sum": "int", "average": "float"}.
                See `pytype2dbtype` for supported types.
            progressbar: str
                if 'notebook', display progressbar as a jupyter notebook widget
                if 'unicode', use unicode (smooth blocks) to fill the progressbar
                if 'ascii', use ASCII characters (1-9 #) to fill the progressbar
                else disable progressbar (default)
        """
        assert (layer_name is None and data_iterator is None and row_mapper is None) is not (tagger is None),\
               'either tagger must be None or layer_name, data_iterator and row_mapper must be None'

        def default_row_mapper(row):
            text_id, text = row[0], row[1]
            layer = tagger.make_layer(text=text)
            return [RowMapperRecord(layer=layer, meta=None)]

        layer_name = layer_name or tagger.output_layer
        row_mapper = row_mapper or default_row_mapper
        data_iterator = data_iterator or self.select(layers=tagger.input_layers, progressbar=progressbar)

        if not self.exists():
            raise PgCollectionException("collection {!r} does not exist, can't create layer {!r}".format(
                self.table_name, layer_name))
        logger.info('collection: {!r}'.format(self.table_name))
        if self._structure is None:
            raise PgCollectionException("can't add detached layer {!r}, the collection is empty".format(layer_name))
        if self.has_layer(layer_name):
            if overwrite:
                logger.info("overwriting output layer: {!r}".format(layer_name))
                self.delete_layer(layer_name=layer_name, cascade=True)
            else:
                exception = PgCollectionException("can't create layer {!r}, layer already exists".format(layer_name))
                logger.error(exception)
                raise exception
        logger.info('preparing to create a new layer: {!r}'.format(layer_name))
        conn = self.storage.conn
        with conn.cursor() as c:
            try:
                conn.autocommit = False
                # create table and indices
                self.create_layer_table(cursor=c,
                                        layer_name=layer_name,
                                        create_index=create_index,
                                        ngram_index=ngram_index,
                                        overwrite=overwrite,
                                        meta=meta)
                # insert data
                id_ = 0

                meta_columns = ()
                if meta is not None:
                    meta_columns = tuple(meta)

                for row in data_iterator:
                    collection_id, text = row[0], row[1]
                    for record in row_mapper(row):
                        layer = record.layer
                        layer_dict = layer_to_dict(layer, text)
                        layer_json = json.dumps(layer_dict, ensure_ascii=False)

                        columns = ["id", "text_id", "data"]
                        values = [id_, collection_id, layer_json]

                        if meta_columns:
                            columns.extend(meta_columns)
                            values.extend(record.meta[k] for k in meta_columns)

                        if ngram_index is not None:
                            ngram_index_keys = tuple(ngram_index.keys())
                            columns.extend(ngram_index_keys)
                            values.extend(create_ngram_fingerprint_index(layer=layer,
                                                                         attribute=attr,
                                                                         n=ngram_index[attr])
                                          for attr in ngram_index_keys)

                        columns = SQL(', ').join(map(Identifier, columns))
                        q = SQL('INSERT INTO {} ({}) VALUES ({});'
                                ).format(self._layer_identifier(layer_name),
                                         columns,
                                         SQL(', ').join(map(Literal, values)))
                        c.execute(q)
                        logger.debug('insert into layer {!r}, query size: {} bytes'.format(layer_name, len(c.query)))

                        id_ += 1
                self._insert_into_structure(layer, detached=True, meta=meta)
            except:
                conn.rollback()
                raise
            finally:
                if conn.status == STATUS_BEGIN:
                    # no exception, transaction in progress
                    conn.commit()
                conn.autocommit = True

        logger.info('layer created: {!r}'.format(layer_name))

    def continue_creating_layer(self, tagger, progressbar=None, query_length_limit=5000000):
        self.create_layer_buffered(tagger=tagger, progressbar=progressbar, query_length_limit=query_length_limit,
                                   mode='append')

    # TODO: rename to create_layer
    def create_layer_buffered(self, layer_name=None, data_iterator=None, row_mapper=None, tagger=None,
                              create_index=False, ngram_index=None, overwrite=False, meta=None, progressbar=None,
                              query_length_limit=5000000, mode=None):
        """
        Creates layer

        Args:
            layer_name:
            data_iterator: iterator
                Iterator over Text collection which generates tuples (`text_id`, `text`).
                See method `PgCollection.select`.
            row_mapper: function
                For each record produced by `data_iterator` return a list
                of `RowMapperRecord` objects.
            tagger: Tagger
                either tagger must be None or layer_name, data_iterator and row_mapper must be None
            create_index: bool
                Whether to create an index on json column
            ngram_index: list
                A list of attributes for which to create an ngram index
            overwrite: bool
                deprecated, use mode='overwrite' instead
                If True and layer table exists, table is overwritten.
                If False and layer table exists, error is raised.
            meta: dict of str -> str
                Specifies table column names and data types to create for storing additional
                meta information. E.g. meta={"sum": "int", "average": "float"}.
                See `pytype2dbtype` for supported types.
            progressbar: str
                if 'notebook', display progressbar as a jupyter notebook widget
                if 'unicode', use unicode (smooth blocks) to fill the progressbar
                if 'ascii', use ASCII characters (1-9 #) to fill the progressbar
                else disable progressbar (default)
            query_length_limit: int
                soft approximate query length limit in unicode characters, can be exceeded by the length of last buffer
                insert
        """
        assert (layer_name is None and data_iterator is None and row_mapper is None) is not (tagger is None),\
               'either tagger ({}) must be None or layer_name ({}), data_iterator ({}) and row_mapper ({}) must be None'.format(tagger, layer_name, data_iterator, row_mapper)

        # TODO: remove overwrite parameter
        assert overwrite is False or mode is None, (overwrite, mode)
        if overwrite:
            mode = 'overwrite'
        mode = mode or 'new'

        def default_row_mapper(row):
            text_id, text = row[0], row[1]
            status = {}
            layer = tagger.make_layer(text=text, status=status)
            return [RowMapperRecord(layer=layer, meta=status)]

        layer_name = layer_name or tagger.output_layer
        row_mapper = row_mapper or default_row_mapper

        missing_layer = layer_name if mode == 'append' else None
        data_iterator = data_iterator or self.select(layers=tagger.input_layers, progressbar=progressbar,
                                                     missing_layer=missing_layer)

        if not self.exists():
            raise PgCollectionException("collection {!r} does not exist, can't create layer {!r}".format(
                self.table_name, layer_name))
        logger.info('collection: {!r}'.format(self.table_name))
        if self._structure is None:
            raise PgCollectionException("can't add detached layer {!r}, the collection is empty".format(layer_name))
        if self.has_layer(layer_name):
            if mode == 'overwrite':
                logger.info("overwriting output layer: {!r}".format(layer_name))
                self.delete_layer(layer_name=layer_name, cascade=True)
            elif mode == 'append':
                logger.info("appending existing layer: {!r}".format(layer_name))
            else:
                exception = PgCollectionException("can't create layer {!r}, layer already exists".format(layer_name))
                logger.error(exception)
                raise exception
        else:
            if mode == 'append':
                exception = PgCollectionException("can't append layer {!r}, layer does not exist".format(layer_name))
                logger.error(exception)
                raise exception
            elif mode == 'new':
                logger.info('preparing to create a new layer: {!r}'.format(layer_name))
            elif mode == 'overwrite':
                logger.info('nothing to overwrite, preparing to create a new layer: {!r}'.format(layer_name))

        conn = self.storage.conn

        meta_columns = ()
        if meta is not None:
            meta_columns = tuple(meta)

        columns = ["id", "text_id", "data"]
        if meta_columns:
            columns.extend(meta_columns)

        if ngram_index is not None:
            ngram_index_keys = tuple(ngram_index.keys())
            columns.extend(ngram_index_keys)

        with conn.cursor() as c:
            try:
                conn.autocommit = True
                # create table and indices
                if mode in {'new', 'overwrite'}:
                    self.create_layer_table(cursor=c,
                                            layer_name=layer_name,
                                            create_index=create_index,
                                            ngram_index=ngram_index,
                                            overwrite=(mode == 'overwrite'),
                                            meta=meta)
                # insert data
                structure_written = (mode == 'append')
                with self.buffered_layer_insert(table_identifier=self._layer_identifier(layer_name),
                                                columns=columns,
                                                query_length_limit=query_length_limit) as buffered_insert:
                    for row in data_iterator:
                        collection_id, text = row[0], row[1]
                        for record in row_mapper(row):
                            layer = record.layer
                            layer_dict = layer_to_dict(layer, text)
                            layer_json = json.dumps(layer_dict, ensure_ascii=False)

                            values = [None, collection_id, layer_json]

                            if meta_columns:
                                values.extend(record.meta[k] for k in meta_columns)

                            if ngram_index is not None:
                                values.extend(create_ngram_fingerprint_index(layer=layer,
                                                                             attribute=attr,
                                                                             n=ngram_index[attr])
                                              for attr in ngram_index_keys)
                            values = list(map(Literal, values))
                            values[0] = DEFAULT
                            buffered_insert(values=values)
                            if not structure_written:
                                self._insert_into_structure(layer, detached=True, meta=meta)
                                structure_written = True
            except Exception:
                conn.rollback()
                raise
            finally:
                if conn.status == STATUS_BEGIN:
                    # no exception, transaction in progress
                    conn.commit()
                conn.autocommit = True

        logger.info('layer created: {!r}'.format(layer_name))

    def create_layer_table(self, cursor, layer_name, create_index=True, ngram_index=None, overwrite=False, meta=None):
        is_fragment = False
        table_name = self.layer_name_to_table_name(layer_name)
        return self._create_layer_table(cursor, table_name, layer_name, is_fragment, create_index, ngram_index,
                                        overwrite=overwrite, meta=meta)

    def create_fragment_table(self, cursor, fragment_name, create_index=True, ngram_index=None):
        is_fragment = True
        table_name = self.fragment_name_to_table_name(fragment_name)
        return self._create_layer_table(cursor, table_name, fragment_name, is_fragment, create_index, ngram_index)

    def _create_layer_table(self, cursor, layer_table, layer_name, is_fragment=False, create_index=True,
                            ngram_index=None, overwrite=False, meta=None):
        if overwrite:
            self.storage.drop_table_if_exists(layer_table)
        elif self.storage.table_exists(layer_table):
            raise PgStorageException("Table {!r} for layer {!r} already exists.".format(layer_table, layer_name))

        if self._temporary:
            temporary = SQL('TEMPORARY')
        else:
            temporary = SQL('')

        # create layer table and index
        q = ('CREATE {temporary} TABLE {layer_identifier} ('
             'id SERIAL PRIMARY KEY, '
             '%(parent_col)s'
             'text_id int NOT NULL, '
             'data jsonb'
             '%(meta_cols)s'
             '%(ngram_cols)s);')

        if is_fragment is True:
            parent_col = "parent_id int NOT NULL,"
        else:
            parent_col = ""

        if ngram_index is not None:
            ngram_cols = ", %s" % ",".join(["%s text[]" % Identifier(column).as_string(self.storage.conn)
                                            for column in ngram_index])
        else:
            ngram_cols = ""

        if meta is not None:
            cols = [Identifier(col).as_string(self.storage.conn) for col in meta.keys()]
            types = [pytype2dbtype[py_type] for py_type in meta.values()]
            meta_cols = ", %s" % ",".join(["%s %s" % (c, d) for c, d in zip(cols, types)])
        else:
            meta_cols = ""

        q %= {"parent_col": parent_col, "ngram_cols": ngram_cols, "meta_cols": meta_cols}
        if is_fragment:
            layer_identifier = self._fragment_identifier(layer_name)
        else:
            layer_identifier = self._layer_identifier(layer_name)
        q = SQL(q).format(temporary=temporary, layer_identifier=layer_identifier)
        cursor.execute(q)
        logger.debug(cursor.query.decode())

        q = SQL("COMMENT ON TABLE {} IS {};").format(
            layer_identifier,
            Literal("%s %s layer" % (self.table_name, layer_name)))
        cursor.execute(q)
        logger.debug(cursor.query.decode())

        # create jsonb index
        if create_index is True:
            cursor.execute(SQL(
                "CREATE INDEX {index} ON {schema}.{table} USING gin ((data->'layers') jsonb_path_ops);").format(
                schema=Identifier(self.storage.schema),
                index=Identifier('idx_%s_data' % layer_table),
                table=Identifier(layer_table)))
            logger.debug(cursor.query.decode())

        # create ngram array index
        if ngram_index is not None:
            for column in ngram_index:
                cursor.execute(SQL(
                    "CREATE INDEX {index} ON {schema}.{table} USING gin ({column});").format(
                    schema=Identifier(self.storage.schema),
                    index=Identifier('idx_%s_%s' % (layer_table, column)),
                    table=Identifier(layer_table),
                    column=Identifier(column)))
                logger.debug(cursor.query.decode())

        cursor.execute(SQL(
            "CREATE INDEX {index} ON {layer_table} (text_id);").format(
            index=Identifier('idx_%s__text_id' % layer_table),
            layer_table=layer_identifier))
        logger.debug(cursor.query.decode())

    def delete_layer(self, layer_name, cascade=False):
        if layer_name not in self._structure:
            raise PgCollectionException("collection does not have a layer {!}".format(layer_name))
        if not self._structure[layer_name]['detached']:
            raise PgCollectionException("can't delete attached layer {!}".format(layer_name))

        for ln, struct in self._structure.items():
            if ln == layer_name:
                continue
            if layer_name == struct['enveloping'] or layer_name == struct['parent'] or layer_name == struct['_base']:
                if cascade:
                    self.delete_layer(ln, cascade=True)
                else:
                    raise PgCollectionException("can't delete layer {!r}; "
                                                "there is a dependant layer {!r}".format(layer_name, ln))
        self._drop_table(self._layer_identifier(layer_name))
        self._delete_from_structure(layer_name)
        logger.info('layer deleted: {!r}'.format(layer_name))

    def delete_fragment(self, fragment_name):
        fragment_table = self.fragment_name_to_table_name(fragment_name)
        if fragment_name not in self.get_fragment_names():
            raise PgStorageException("Collection does not have a layer fragment '%s'." % fragment_name)
        if not self.storage.table_exists(fragment_table):
            raise PgStorageException("Layer fragment table '%s' does not exist." % fragment_table)
        self.storage.drop_table(fragment_table)

    def delete_layer_fragment(self, layer_fragment_name):
        lf_table = self.layer_fragment_name_to_table_name(layer_fragment_name)
        if layer_fragment_name not in self.get_layer_fragment_names():
            raise PgStorageException("Collection does not have a layer fragment '%s'." % layer_fragment_name)
        if not self.storage.table_exists(lf_table):
            raise PgStorageException("Layer fragment table '%s' does not exist." % lf_table)
        self.storage.drop_table(lf_table)

    def delete(self):
        """Removes collection and all related layers."""
        conn = self.storage.conn
        conn.autocommit = False
        try:
            for identifier in self._get_layer_table_identifiers():
                self._drop_table(identifier)
            self._drop_table(self._structure_identifier())
            self._drop_table(self._collection_identifier())
        except Exception:
            conn.rollback()
            raise
        finally:
            if conn.status == STATUS_BEGIN:
                # no exception, transaction in progress
                conn.commit()
            conn.autocommit = True
            logger.info('collection {!r} deleted'.format(self.table_name))

    def _drop_table(self, identifier):
        with self.storage.conn.cursor() as c:
            c.execute(SQL('DROP TABLE {};').format(identifier))
            logger.debug(c.query.decode())

    def has_layer(self, layer_name):
        return layer_name in self._structure

    def has_fragment(self, fragment_name):
        return fragment_name in self.get_fragment_names()

    def get_fragment_names(self):
        lf_names = []
        for tbl in self.get_fragment_tables():
            layer = re.sub("^%s__" % self.table_name, "", tbl)
            layer = re.sub("__fragment$", "", layer)
            lf_names.append(layer)
        return lf_names

    def get_layer_names(self):
        return list(self._structure)

    def get_fragment_tables(self):
        fragment_tables = []
        for tbl in self.storage.get_all_table_names():
            if tbl.startswith("%s__" % self.table_name) and tbl.endswith("__fragment"):
                fragment_tables.append(tbl)
        return fragment_tables

    def _get_layer_table_identifiers(self):
        identifiers = []
        if not self._structure:
            return identifiers
        for name, struct in self._structure.items():
            if struct['detached']:
                identifiers.append(self._layer_identifier(name))
        return identifiers

    def get_layer_meta(self, layer_name):
        layer_table = self.layer_name_to_table_name(layer_name)
        if layer_name not in self.get_layer_names():
            raise PgStorageException("Collection does not have a layer '{}'.".format(layer_name))
        if not self.storage.table_exists(layer_table):
            raise PgStorageException("Layer table '{}' does not exist.".format(layer_table))

        with self.storage.conn.cursor() as c:
            c.execute(SQL("SELECT column_name FROM information_schema.columns "
                          "WHERE table_schema=%s AND table_name=%s;"),
                      (self.storage.schema, layer_table))
            res = c.fetchall()
            columns = [r[0] for r in res if r[0] != 'data']

            c.execute(SQL('SELECT {} FROM {}.{};').format(
                SQL(', ').join(map(Identifier, columns)),
                Identifier(self.storage.schema),
                Identifier(layer_table)))
            data = c.fetchall()
            return pandas.DataFrame(data=data, columns=columns)

    def export_layer(self, layer, attributes, progressbar=None):
        export_table = '{}__{}__export'.format(self.table_name, layer)
        texts = self.select(layers=[layer], progressbar=progressbar)
        logger.info('preparing to export layer {!r} with attributes {!r}'.format(layer, attributes))

        columns = [
            ('id', 'serial PRIMARY KEY'),
            ('text_id', 'int NOT NULL'),
            ('span_nr', 'int NOT NULL')]
        columns.extend((attr, 'text') for attr in attributes)

        columns_sql = SQL(",\n").join(SQL("{} {}").format(Identifier(n), SQL(t)) for n, t in columns)

        i = 0
        with self.storage.conn.cursor() as c:
            c.execute(SQL("DROP TABLE IF EXISTS {}.{};").format(Identifier(self.storage.schema),
                                                                Identifier(export_table)))
            logger.debug(c.query)
            c.execute(SQL("CREATE TABLE {}.{} ({});").format(Identifier(self.storage.schema),
                                                             Identifier(export_table),
                                                             columns_sql))
            logger.debug(c.query)

            for text_id, text in texts:
                for span_nr, span in enumerate(text[layer]):
                    for annotation in span:
                        i += 1
                        values = [i, text_id, span_nr]
                        values.extend(str(getattr(annotation, attr)) for attr in attributes)
                        c.execute(SQL("INSERT INTO {}.{} "
                                      "VALUES ({});").format(Identifier(self.storage.schema),
                                                            Identifier(export_table),
                                                            SQL(', ').join(map(Literal, values))
                                                            ))
        logger.info('{} annotations exported to "{}"."{}"'.format(i, self.storage.schema, export_table))

    def _repr_html_(self):
        return ('<h3>Collection</h3><br/>name: {}'
                '<h4>Layers</h4>structure table').format(self.table_name)


class PostgresStorage:
    """`PostgresStorage` instance wraps a database connection and
    exposes interface to conveniently search/save json data.
    """

    def __init__(self, dbname=None, user=None, password=None, host=None, port=None,
                 pgpass_file=None, schema="public", role=None, **kwargs):
        """
        Connects to database either using connection parameters if specified, or ~/.pgpass file.

            ~/.pgpass file format: hostname:port:database:username:password

        """
        self.schema = schema
        _host, _port, _dbname, _user, _password = host, port, dbname, user, password
        if _host is None or _port is None or _dbname is None or _user is None or _password is None:
            if pgpass_file is None:
                raise PgStorageException("If 'host', 'port', 'dbname', 'user' or 'password' is None, "
                                         "then 'pgpass_file' must not be None.")
            pgpass = os.path.expanduser(pgpass_file)
            if not os.path.isfile(pgpass):
                raise PgStorageException('pgpass file {!r} not found.'.format(pgpass))
            with open(pgpass, encoding="utf-8") as f:
                for line in f:
                    line_split = line.rstrip().split(':')
                    if line.startswith('#') or len(line_split) != 5:
                        continue
                    f_host, f_port, f_dbname, f_user, f_password = line_split

                    _host = f_host
                    if host is None:
                        if f_host == '*':
                            continue
                    elif f_host in {'*', host}:
                        _host = host
                    else:
                        continue

                    _port = f_port
                    if port is None:
                        if f_port == '*':
                            continue
                    elif f_port in {'*', port}:
                        _port = port
                    else:
                        continue

                    _dbname = f_dbname
                    if dbname is None:
                        if f_dbname == '*':
                            continue
                    elif f_dbname in {'*', dbname}:
                        _dbname = dbname
                    else:
                        continue

                    _user = f_user
                    if user is None:
                        if f_user == '*':
                            continue
                    elif f_user in {'*', user}:
                        _user = user
                    else:
                        continue

                    _password = password or f_password
                    break

            if _password is None:
                raise PgStorageException(('no password found for '
                                          'host: {}, port: {}, dbname: {}, user: {}'
                                          ).format(host, port, dbname, user))
        if role is None:
            role = _user
        logger.info('connecting to host: {!r}, port: {!r}, dbname: {!r}, user: {!r}'.format(_host, _port, _dbname, _user))

        try:
            self.conn = psycopg2.connect(dbname=_dbname, user=_user, password=_password, host=_host, port=_port,
                                         **kwargs)
        except Exception:
            logger.error('Failed to connect '
                         'host: {!r}, port: {!r}, dbname: {!r}, user: {!r}.'.format(_host, _port, _dbname, _user))
            raise
        self.conn.autocommit = True

        with self.conn.cursor() as c:
            logger.info('role: {!r}'.format(role))
            c.execute(SQL("SET ROLE {};").format(Identifier(role)))

    def close(self):
        """Closes database connection"""
        self.conn.close()

    def create_schema(self):
        with self.conn.cursor() as c:
            c.execute(SQL("CREATE SCHEMA {};").format(Identifier(self.schema)))

    def delete_schema(self):
        with self.conn.cursor() as c:
            c.execute(SQL("DROP SCHEMA {} CASCADE;").format(Identifier(self.schema)))

    def create_table(self, table, description=None, meta=None, temporary=False, table_identifier=None):
        """Creates a new table to store jsonb data:

            CREATE TABLE table(
                id serial PRIMARY KEY,
                data jsonb
            );

        and automatically adds a GIN index for the jsonb column:

            CREATE INDEX idx_table_data ON table USING gin ((data -> 'layers') jsonb_path_ops);
        """
        columns = [SQL('id BIGSERIAL PRIMARY KEY'),
                   SQL('data jsonb')]
        if meta is not None:
            for col_name, col_type in meta.items():
                columns.append(SQL('{} {}').format(Identifier(col_name), SQL(pytype2dbtype[col_type])))

        temp = SQL('TEMPORARY') if temporary else SQL('')
        table_identifier = table_identifier or SQL('{}.{}').format(Identifier(self.schema), Identifier(table))

        self.conn.autocommit = False
        with self.conn.cursor() as c:
            try:
                c.execute(SQL("CREATE {} TABLE {} ({});").format(
                    temp, table_identifier, SQL(', ').join(columns)))
                logger.debug(c.query.decode())
                c.execute(
                    SQL("CREATE INDEX {index} ON {table} USING gin ((data->'layers') jsonb_path_ops);").format(
                        index=Identifier('idx_%s_data' % table),
                        table=table_identifier))
                logger.debug(c.query.decode())
                if isinstance(description, str):
                    c.execute(SQL("COMMENT ON TABLE {} IS {}").format(
                        table_identifier, Literal(description)))
                    logger.debug(c.query.decode())
            except:
                self.conn.rollback()
                raise
            finally:
                if self.conn.status == STATUS_BEGIN:
                    # no exception, transaction in progress
                    self.conn.commit()
                self.conn.autocommit = True

    @staticmethod
    def fragment_name_to_table_name(collection_table, fragment_name):
        """
        Constructs table name for a fragment.

        Args:
            collection_table: str
                parent collection table
            fragment_name: str
                fragment name
        Returns:
            str: fragment table name

        """
        return "%s__%s__fragment" % (collection_table, fragment_name)

    @staticmethod
    def layer_name_to_table_name(collection_table, layer_name):
        """
        Constructs layer table name.

        Args:
            collection_table: str
                parent collection table
            layer_name: str
                layer name
        Returns:
            str: layer table name

        """
        return "%s__%s__layer" % (collection_table, layer_name)

    def drop_table(self, table):
        with self.conn.cursor() as c:
            c.execute(SQL("DROP TABLE {}.{};").format(Identifier(self.schema), Identifier(table)))
            logger.debug(c.query.decode())

    def drop_table_if_exists(self, table):
        with self.conn.cursor() as c:
            c.execute(SQL("DROP TABLE IF EXISTS {}.{};").format(Identifier(self.schema), Identifier(table)))

    def insert_layer_row(self, layer_table, layer_dict, row_id, text_id, ngram_values=None):
        layer_json = json.dumps(layer_dict, ensure_ascii=False)
        ngram_values = ngram_values or []
        with self.conn.cursor() as c:
            sql = "INSERT INTO {}.{} VALUES (%s) RETURNING id;" % ", ".join(['%s'] * (3 + len(ngram_values)))
            c.execute(SQL(sql).format(Identifier(self.schema), Identifier(layer_table)),
                      (row_id, text_id, layer_json, *ngram_values))
            row_key = c.fetchone()[0]
            return row_key

    def insert(self, table, text, key=None, meta=None):
        """
        Saves a given `text` object into a given `table`..
        Args:
            table: str
            text: text
            key: int

        Returns:
            int: row key (id)
        """
        text = text_to_json(text)
        if key is None:
            key = DEFAULT
        else:
            key = Literal(key)
        with self.conn.cursor() as c:
            c.execute(SQL("INSERT INTO {}.{} VALUES ({}, %s) RETURNING id").format(
                Identifier(self.schema), Identifier(table), key), (text,))
            row_key = c.fetchone()[0]
            return row_key

    def table_exists(self, table, schema=None):
        if schema is None:
            schema = self.schema
        with self.conn.cursor() as c:
            c.execute(SQL("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = %s AND tablename = %s);"),
                      [schema, table])
            return c.fetchone()[0]

    def count_rows(self, table=None, table_identifier=None):
        if table_identifier is not None:
            with self.conn.cursor() as c:
                c.execute(SQL("SELECT count(*) FROM {}").format(table_identifier))
                return c.fetchone()[0]
        with self.conn.cursor() as c:
            c.execute(SQL("SELECT count(*) FROM {}.{}").format(Identifier(self.schema), Identifier(table)))
            nrows = c.fetchone()[0]
            return nrows

    def select_by_key(self, table, key, return_as_dict=False):
        """Loads text object by `key`. If `return_as_dict` is True, returns a text object as dict"""
        with self.conn.cursor() as c:
            c.execute(SQL("SELECT * FROM {}.{} WHERE id = %s").format(Identifier(self.schema), Identifier(table)),
                      (key,))
            res = c.fetchone()
            if res is None:
                raise PgStorageException("Key %s not not found." % key)
            key, text_dict = res
            text = text_dict if return_as_dict is True else dict_to_text(text_dict)
            return text

    def get_all_table_names(self):
        with self.conn.cursor() as c:
            c.execute(SQL(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'"),
                [self.schema])
            table_names = [row[0] for row in c.fetchall()]
            return table_names

    def select_fragment_raw(self, fragment_table, text_table, parent_layer_table, query=None, ngram_query=None):
        """

        Args:
            fragment_table:
            text_table:
            parent_layer_table:
            query:
            ngram_query:

        Returns:
            Iterator of tuples.
            Each tuple has 6 elements:
                text_id
                text
                parent_id
                parent_layer
                fragment_id
                fragment_layer
        """
        # 1. Build query
        q = """
            SELECT
              {text_table}.id, {text_table}.data, {parent_table}.id, {parent_table}.data,
              {fragment_table}.id, {fragment_table}.data
            FROM
              {text_table}, {parent_table}, {fragment_table}
            WHERE
              {fragment_table}.parent_id = {parent_table}.id AND {parent_table}.text_id = {text_table}.id
            """

        format_table = lambda tbl: SQL("{}.{}").format(Identifier(self.schema), Identifier(tbl)).as_string(
            self.conn)

        q = q.format(
            text_table=format_table(text_table),
            parent_table=format_table(parent_layer_table),
            fragment_table=format_table(fragment_table))

        if query is not None:
            # build constraint on fragment's data column
            q = "%s AND %s" % (q, query.eval())

        if ngram_query is not None:
            # build constraint on fragment's ngram index
            ngram_q = " AND ".join([self._build_column_ngram_query(q, col, fragment_table)
                                    for col, q in ngram_query])
            q = "%s AND %s" % (q, ngram_q)

        # 2. Execute query
        with self.conn.cursor() as c:
            c.execute(q)
            for row in c.fetchall():
                text_id, text_dict, parent_id, parent_dict, fragment_id, fragment_dict = row
                text = dict_to_text(text_dict)
                parent_layer = dict_to_layer(parent_dict, text)
                fragment_layer = dict_to_layer(fragment_dict, text)
                yield text_id, text, parent_id, parent_layer, fragment_id, fragment_layer

    def select_raw(self,
                   table: str,
                   query: str = None,
                   layer_query: 'JsonbLayerQuery' = None,
                   layer_ngram_query: dict = None,
                   layers: list = None,
                   keys: list = None,
                   order_by_key: bool = False):
        """
        Select from collection table with possible search constraints.

        Args:
            table: str
                collection table
            query: JsonbTextQuery
                collection table query
            layer_query: JsonbLayerQuery
                layer query
            keys: list
                List of id-s.
            order_by_key: bool
            layers: list
                Layers to fetch. Specified layers will be merged into returned text object and
                become accessible via `text["layer_name"]`.

        Returns:
            iterator of (key, text) pairs

        Example:

            q = JsonbTextQuery('morph_analysis', lemma='laulma')
            for key, txt in storage.select(table, query=q):
                print(key, txt)


        """
        with self.conn.cursor() as c:
            # 1. Build query

            where = False
            sql_parts = []
            table_escaped = SQL("{}.{}").format(Identifier(self.schema), Identifier(table)).as_string(self.conn)
            if not layers and layer_query is None and layer_ngram_query is None:
                # select only text table
                q = SQL("SELECT id, data FROM {}.{}").format(Identifier(self.schema), Identifier(table)).as_string(self.conn)
                sql_parts.append(q)
            else:
                # need to join text and all layer tables
                layers = layers or []
                layer_query = layer_query or {}
                layer_ngram_query = layer_ngram_query or {}

                layers_select = []
                for layer in chain(layers):
                    layer = self.layer_name_to_table_name(table, layer)
                    layer = SQL("{}.{}").format(Identifier(self.schema), Identifier(layer)).as_string(self.conn)
                    layers_select.append(layer)

                layers_join = set()
                for layer in chain(layers, layer_query.keys(), layer_ngram_query.keys()):
                    layer = self.layer_name_to_table_name(table, layer)
                    layer = SQL("{}.{}").format(Identifier(self.schema), Identifier(layer)).as_string(self.conn)
                    layers_join.add(layer)

                q = "SELECT {table}.id, {table}.data {select} FROM {table}, {layers_join} where {where}".format(
                    schema=Identifier(self.schema),
                    table=table_escaped,
                    select=", %s" % ", ".join(
                        "{0}.id, {0}.data".format(layer) for layer in layers_select) if layers_select else "",
                    layers_join=", ".join(layer for layer in layers_join),
                    where=" AND ".join("%s.id = %s.text_id" % (table_escaped, layer) for layer in layers_join))
                sql_parts.append(q)
                where = True
            if query is not None:
                # build constraint on the main text table
                sql_parts.append("%s %s" % ("and" if where else "where", query.eval()))
                where = True
            if layer_query:
                # build constraint on related layer tables
                q = " AND ".join(query.eval() for layer, query in layer_query.items())
                sql_parts.append("%s %s" % ("and" if where else "where", q))
                where = True
            if keys is None:
                keys = []
            else:
                keys = list(map(int, keys))
                # build constraint on id-s
                sql_parts.append("AND" if where else "WHERE")
                sql_parts.append("{table}.id = ANY(%(keys)s)".format(table=table_escaped))
                where = True
            if layer_ngram_query:
                # build constraint on related layer's ngram index
                q = self.build_layer_ngram_query(layer_ngram_query, table)
                if where is True:
                    q = "AND %s" % q
                sql_parts.append(q)
                where = True
            if order_by_key is True:
                sql_parts.append("order by id")

            sql = " ".join(sql_parts)  # bad, bad string concatenation, but we can't avoid it here, right?

            # 2. Execute query
            c.execute(sql, {'keys': keys})
            for row in c.fetchall():
                text_id = row[0]
                text_dict = row[1]
                text = dict_to_text(text_dict)
                layers = []
                if len(row) > 2:
                    detached_layers = {}
                    for i in range(2, len(row), 2):
                        layer_id = row[i]
                        layer_dict = row[i + 1]
                        layer = dict_to_layer(layer_dict, text, detached_layers)
                        detached_layers[layer.name] = layer
                        layers.append(layer_id)
                        layers.append(layer)
                result = text_id, text, *layers
                yield result

    def select(self, table, query=None, layer_query=None, layer_ngram_query=None, layers=None, keys=None,
               order_by_key=False):
        for row in self.select_raw(table, query, layer_query, layer_ngram_query, layers, keys=keys,
                                   order_by_key=order_by_key):
            text_id = row[0]
            text = row[1]
            if len(row) > 2:
                for i, layer_name in zip(range(3, len(row), 2), layers):
                    layer = row[i]
                    text[layer_name] = layer
            yield text_id, text

    def build_layer_ngram_query(self, ngram_query, collection_table):
        sql_parts = []
        for layer in ngram_query:
            for column, q in ngram_query[layer].items():
                layer_table = self.layer_name_to_table_name(collection_table, layer)
                col_query = self._build_column_ngram_query(q, column, layer_table)
                sql_parts.append(col_query)
        q = " AND ".join(sql_parts)
        return q

    def _build_column_ngram_query(self, query, column, table_name):
        if not isinstance(query, list):
            query = list(query)
        if isinstance(query[0], list):
            # case: [[(a),(b)], [(c)]] -> a AND b OR c
            or_terms = [["-".join(e) for e in and_term] for and_term in query]
        elif isinstance(query[0], tuple):
            # case: [(a), (b)] -> a OR b
            or_terms = [["-".join(e)] for e in query]
        elif isinstance(query[0], str):
            # case: [a, b] -> "a-b"
            or_terms = [["-".join(query)]]
        else:
            raise ValueError("Invalid ngram query format: {}".format(query))

        or_parts = []
        for and_term in or_terms:
            arr = ",".join("'%s'" % v for v in and_term)
            p = SQL("{schema}.{table}.{column} @> ARRAY[%s]" % arr).format(
                schema=Identifier(self.schema),
                table=Identifier(table_name),
                column=Identifier(column)).as_string(self.conn)
            or_parts.append(p)
        column_ngram_query = "(%s)" % " OR ".join(or_parts)
        return column_ngram_query

    def find_fingerprint(self, table, query=None, layer_query=None, layer_ngram_query=None, layers=None,
                         order_by_key=False):
        """
        A wrapper over `select` method, which enables to conveniently build composite AND/OR queries.

        Args:
            table: str
                collection table name
            query: dict
                Query applied to collection table
            layer_query: dict
                Query applied to layer table
            order_by_key: bool
                Sort results by key in ascending order
        Returns:
            iterator of tuples (key, text)

        Example `layer_ngramm_query`:

            Search ("üks,kaks" AND "kolm,neli") OR "viis,kuus":

            q = {
                "some_layer": {
                     "field": "some_field",
                     "query": [[("üks", "kaks"), ("kolm", "neli")], [("viis", "kuus")]],
                },
                ...

        Example `query`:

            q = {
                 "layer": "morph_analysis",
                 "field": "lemma",
                 "ambiguous": True,
                 "query": ["mis", "palju"],  # mis OR palju
                 }

        Example `layer_query`:

            q = {
                layer1: {
                    "field": "lemma",
                    "query": ["ööbik"],
                    "ambiguous": True
                },
                layer2: {
                    "field": "lemma",
                    "query": ["ööbik"],
                    "ambiguous": True
                }}
        """
        if query is None and layer_query is None and layer_ngram_query is None:
            raise PgStorageException("One of 'query', 'layer_query' or 'layer_ngramm_query' should be specified.")

        def build_text_query(q):
            or_query_list = []
            for and_terms in q["query"]:
                if not isinstance(and_terms, (list, tuple, set)):
                    and_terms = [and_terms]
                if and_terms:
                    and_query = reduce(op.__and__, (JsonbTextQuery(q["layer"], q["ambiguous"], **{q["field"]: term})
                                                    for term in and_terms))
                    or_query_list.append(and_query)
            if len(or_query_list) > 0:
                jsonb_query = reduce(op.__or__, or_query_list)
            else:
                jsonb_query = None
            return jsonb_query

        def build_layer_query(layer, q):
            or_query_list = []
            layer_table = self.layer_name_to_table_name(table, layer)
            for and_terms in q["query"]:
                if not isinstance(and_terms, (list, tuple, set)):
                    and_terms = [and_terms]
                if and_terms:
                    and_query = reduce(op.__and__,
                                       (JsonbLayerQuery(layer_table, q["ambiguous"], **{q["field"]: term})
                                        for term in and_terms))
                    or_query_list.append(and_query)
            if len(or_query_list) > 0:
                jsonb_query = reduce(op.__or__, or_query_list)
            else:
                jsonb_query = None
            return jsonb_query

        jsonb_text_query = build_text_query(query) if query is not None else None
        jsonb_layer_query = {layer: build_layer_query(layer, q) for layer, q in
                             layer_query.items()} if layer_query is not None else None

        return self.select(table, jsonb_text_query, jsonb_layer_query, layer_ngram_query, layers,
                           order_by_key=order_by_key)

    def get_collection(self, table_name, meta_fields=None, temporary=False):
        """Returns a new instance of `PgCollection` without physically creating it."""
        return PgCollection(name=table_name, storage=self, meta=meta_fields, temporary=temporary)


class JsonbTextQuery(Query):
    """
    Constructs database query to search `text` objects stored in jsonb format.
    """

    def __init__(self, layer, ambiguous=True, **kwargs):
        if not kwargs:
            raise ValueError('At least one layer attribute is required.')
        self.layer = layer
        self.ambiguous = ambiguous
        self.kwargs = kwargs

    def eval(self):
        if self.ambiguous is True:
            pat = """data->'layers' @> '[{"name": "%s", "spans": [[%s]]}]'"""
        else:
            pat = """data->'layers' @> '[{"name": "%s", "spans": [%s]}]'"""
        return pat % (self.layer, json.dumps(self.kwargs))


class JsonbLayerQuery(Query):
    """
    Constructs database query to search `layer` objects stored in jsonb format.
    """

    def __init__(self, layer_table, ambiguous=True, **kwargs):
        if not kwargs:
            raise ValueError('At least one layer attribute is required.')
        self.layer_table = layer_table
        self.ambiguous = ambiguous
        self.kwargs = kwargs

    def eval(self):
        if self.ambiguous is True:
            pat = """%s.data @> '{"spans": [[%s]]}'"""
        else:
            pat = """%s.data @> '{"spans": [%s]}'"""
        return pat % (self.layer_table, json.dumps(self.kwargs))
