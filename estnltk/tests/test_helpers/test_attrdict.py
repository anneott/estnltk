import pytest

from estnltk.helpers.attrdict import AttrDict
from estnltk.tests.helpers.object_inspection import inspect_class_members


def test_len():
    # Empty dict
    attrdict = AttrDict()
    assert len(attrdict) == 0

    # Dict without shadowed attributes
    attrdict = AttrDict(number=42, string='twelve', dict={'a': 15, 'b': 'one'})
    assert len(attrdict) == 3

    # Dict with shadowed attributes
    attrdict = AttrDict(number=42, string='twelve', dict={'a': 15, 'b': 'one'},
                        methods=5, keys=['a', 'b'], __len__='its gonna fail without arrangements')
    assert len(attrdict) == 6


def test_methods_list():
    # Test that the list of prohibited attribute names is complete
    members = inspect_class_members(AttrDict())
    assert set(members['properties']) <= AttrDict.methods
    assert set(members['private_methods']) <= AttrDict.methods
    assert set(members['protected_methods']) <= AttrDict.methods
    assert set(members['public_methods']) <= AttrDict.methods
    assert set(members['private_variables']) <= AttrDict.methods
    assert set(members['protected_variables']) <= AttrDict.methods
    assert set(members['public_variables']) <= AttrDict.methods
    assert set(members['slots']) <= AttrDict.methods


def test_attribute_assignment_and_access():
    # Adding normal attributes
    attrdict = AttrDict()
    attrdict.attr_1 = 'üks'
    attrdict.attr_2 = 1
    attrdict.attr_3 = dict(a=1, b=2)
    assert len(attrdict) == 3
    assert attrdict.attr_1 == 'üks'
    assert attrdict.attr_2 == 1
    assert attrdict.attr_3 == dict(a=1, b=2)
    assert attrdict['attr_1'] == 'üks'
    assert attrdict['attr_2'] == 1
    assert attrdict['attr_3'] == dict(a=1, b=2)

    # Tests that AttrDict methods cannot be assigned
    attrdict = AttrDict()
    for attr in AttrDict.methods:
        with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
            setattr(attrdict, attr, 42)

    # Manual tests for critical methods
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.methods = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.mapping = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.__dict__ = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.__slots__ = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.keys = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.items = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.values = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        attrdict.get = 42


def test_attribute_deletion():
    # Deleting normal attributes
    attrdict = AttrDict(number=42, string='twelve', dict={'a': 15, 'b': 'one'})
    assert len(attrdict) == 3
    assert attrdict.mapping == dict(number=42, string='twelve', dict={'a': 15, 'b': 'one'})
    del attrdict.number
    assert len(attrdict) == 2
    assert attrdict.mapping == dict(string='twelve', dict={'a': 15, 'b': 'one'})
    del attrdict.string
    assert len(attrdict) == 1
    assert attrdict.mapping == dict(dict={'a': 15, 'b': 'one'})
    del attrdict.dict
    assert len(attrdict) == 0
    assert attrdict.mapping == dict()

    # Tests that AttrDict methods cannot be deleted
    attrdict = AttrDict()
    for attr in AttrDict.methods:
        with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
            delattr(attrdict, attr)

    # Manual tests for critical methods
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.methods
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.mapping
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.__dict__
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.__slots__
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.keys
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.items
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.values
    with pytest.raises(AttributeError, match="'AttrDict' object has no attribute"):
        del attrdict.get


def test_item_assignment_and_access():
    # Adding normal keys
    attrdict = AttrDict()
    attrdict['attr_1'] = 'üks'
    attrdict['attr_2'] = 1
    attrdict['attr_3'] = dict(a=1, b=2)
    assert len(attrdict) == 3
    assert attrdict.attr_1 == 'üks'
    assert attrdict.attr_2 == 1
    assert attrdict.attr_3 == dict(a=1, b=2)
    assert attrdict['attr_1'] == 'üks'
    assert attrdict['attr_2'] == 1
    assert attrdict['attr_3'] == dict(a=1, b=2)

    # Tests that AttrDict methods can be keys
    attrdict = AttrDict()
    for attr in AttrDict.methods:
        attrdict[attr] = 42
        assert attrdict[attr] == 42
        assert attr not in attrdict.__dict__

    # Manual tests for critical methods
    attrdict = AttrDict()
    for attr in ['methods', 'mapping', '__dict__', '__slots__', 'keys', 'items', 'values', 'get']:
        attrdict[attr] = 42
        assert attrdict[attr] == 42
        assert attr not in attrdict.__dict__

    # Check that item assignment and deletion correctly updates __dict__
    attrdict = AttrDict(number=42, string='twelve', dict={'a': 15, 'b': 'one'},
                        methods=5, keys=['a', 'b'], __len__='its gonna fail without arrangements')
    assert attrdict.__dict__ == dict(number=42, string='twelve', dict={'a': 15, 'b': 'one'})

    attrdict['new'] = 56
    assert attrdict.__dict__ == dict(number=42, string='twelve', dict={'a': 15, 'b': 'one'}, new=56)

    del attrdict['new']
    assert attrdict.__dict__ == dict(number=42, string='twelve', dict={'a': 15, 'b': 'one'})

    del attrdict['__len__']
    assert attrdict.__dict__ == dict(number=42, string='twelve', dict={'a': 15, 'b': 'one'})


def test_other_dict_functions():
    # Dict with shadowed attributes
    attrdict = AttrDict(number=1, string=2, dict=3, methods=4, keys=5, __len__=6)

    assert set(attrdict.keys()) == {'number', 'string', 'dict', 'methods', 'keys', '__len__'}
    assert set(attrdict.values()) == {1, 2, 3, 4, 5, 6}
    assert set(attrdict.items()) == {('number', 1), ('string', 2), ('dict', 3),
                                     ('methods', 4), ('keys', 5), ('__len__', 6)}

    for key in attrdict.keys():
        assert attrdict[key] == attrdict.get(key)
        assert attrdict[key] == attrdict.get(key, 42)

    assert attrdict.get('missing') is None
    assert attrdict.get('missing', None) is None
    assert attrdict.get('missing', 42) == 42


def test_inheritance():
    # Subclassing AttrDict by reserving new methods
    class SubClass(AttrDict):
        methods = AttrDict.methods | {'new_method'}
        pass

    # Check that list uf protected methods is correct
    subdict = SubClass()
    assert type(SubClass.methods) == frozenset
    assert type(subdict.methods) == frozenset

    # Manual test that inheritance preserves checks
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        subdict.methods = 42
    with pytest.raises(AttributeError, match='attempt to set an attribute that shadows a method'):
        subdict.new_method = 42
    with pytest.raises(AttributeError, match="'SubClass' object has no attribute"):
        del subdict.methods
    with pytest.raises(AttributeError, match="'SubClass' object has no attribute"):
        del subdict.new_method
    with pytest.raises(KeyError, match="'SubClass' object does not have a key"):
        _ = subdict['missing']

    # Default inherited initialisation is correct
    subdict = SubClass(number=42, string='twelve', dict={'a': 15, 'b': 'one'},
                       methods=5, keys=['a', 'b'], __len__='its gonna fail without arrangements')
    assert subdict.mapping == dict(number=42, string='twelve', dict={'a': 15, 'b': 'one'},
                                   methods=5, keys=['a', 'b'], __len__='its gonna fail without arrangements')
    assert subdict.__dict__ == dict(number=42, string='twelve', dict={'a': 15, 'b': 'one'})

    # Test that adding slots works out of box
    class SubClassWithSlots(AttrDict):
        __slots__ = ['new_slot']
        methods = AttrDict.methods
        pass

    subdict = SubClassWithSlots()
    assert len(subdict) == 0
    assert subdict.mapping == {}
    subdict.new_slot = 42
    assert len(subdict) == 0
    assert subdict.mapping == {}
    subdict['new_slot'] = 55
    assert len(subdict) == 1
    assert subdict.mapping == {'new_slot': 55}
    assert subdict.new_slot == 42

    subdict = SubClassWithSlots(new_slot=55, attr=44)
    assert len(subdict) == 2
    assert subdict.mapping == {'new_slot': 55, 'attr': 44}
    with pytest.raises(AttributeError):
        assert subdict.new_slot is None





