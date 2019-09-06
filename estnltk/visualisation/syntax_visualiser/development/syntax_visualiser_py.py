import html

def css():
    with open("syntax_visualiser_css.css") as css_file:
        contents = css_file.read()
        output = ''.join(["<style>\n", contents, "</style>"])
    return output

def event_handler_code():
        with open("syntax_visualiser_js.js") as js_file:
            contents = js_file.read()
            output = ''.join(["<script>\n", contents, "</script>"])
            # output = ''.join(["<script>\n var text_id=", str(self._text_id),"\n", contents, "</script>"])
        return output

def table_column(layers, attribute, deprel, text, index = None, sentence = None):
    cellid = 0
    if sentence is None:
        sentence = 0
    word = 0
    if index is not None:
        table_elements = ["<td><table><tr><th>", attribute, str(index), "</th></tr>"]
    else:
        table_elements = ["<td><table><tr><th>", attribute, "</th></tr>"]
    if attribute == "feats":
        for element in getattr(layers, attribute):
            table_elements.extend(["<tr><td id = \"", str(attribute), str(sentence), ";", str(index), ";", str(cellid), "\">"])
            cellid +=1
            if element is not None:
                for key in element:
                    table_elements.extend([str(key), " "])
            else:
                table_elements.append(str(element))
            table_elements.append("</td></tr>")
    elif attribute == "deprel":
        for element in getattr(layers, attribute):
            table_elements.extend(["<tr><td id = \"", str(attribute), str(sentence), ";", str(index), ";", str(cellid), "\">"])
            cellid += 1
            table_elements.extend(["<select id = \"deprel", str(sentence), ";", str(index), ";", str(cellid), "\"><option value=\"", str(cellid), ";original\">", html.escape(element), "</option>"])
            for deprel_element in deprel:
                if element != deprel_element:
                    table_elements.extend(["<option value=", str(sentence), ";", str(cellid), ";", deprel_element, ">", str(deprel_element), "</option>"])
            table_elements.extend(["</select>", "</td></tr>"])
    elif attribute == "head":
        for element in getattr(layers, attribute):
            if word == len(text.sentences[sentence]):
                word = 0
                sentence += 1
            table_elements.extend(["<tr><td id = \"", str(attribute), str(sentence), ";", str(index), ";", str(cellid), "\">"])
            cellid += 1
            if element != 0:
                table_elements.extend(["<select id=\"head", str(sentence), ";", str(index), ";", str(cellid)," onchange=\"get_select_value();\"><option value=\"", str(cellid), ";original\">", str(element), ": ", str(text.sentences[sentence].text[element - 1]),  "</option><option value=\"", str(cellid), ";0\">", "0", "</option>"])
            else:
                table_elements.extend(["<select id=\"head", str(sentence), ";", str(index), ";", str(cellid), " onchange=\"get_select_value();\"><option value=\"", str(cellid), ";original\">", str(element), "</option>"])
            for i in range(len(text.sentences[sentence])):
                table_elements.extend(["<option value=", str(sentence), ";", str(cellid), ";", str(i + 1), ">", str(i + 1), ": ", str(text.sentences[sentence].text[i]), "</option>"])
            word += 1
            table_elements.append("</select></td></tr>")
    else:
        for element in getattr(layers, attribute):
            table_elements.extend(["<tr><td id = \"", str(attribute), str(sentence), ";", str(index), ";", str(cellid), "\">", str(element), "</td></tr>"])
            cellid += 1
    table_elements.append("</table></td>")
    return table_elements

def table(layer, attributes, deprel, text):
    table_elements = [css(), "<table class=\"iterable-table\"><tr>"]
    for attribute in attributes:
        table_elements.extend(table_column(layer, attribute, deprel, text))
    table_elements.append("</tr></table>")
    return "".join(table_elements)

def joint_table(layers, attributes, deprel, text, sentence = None):
    table_elements = [css(), event_handler_code(), "<table class=\"iterable-table\"><tr>"]
    for attribute in attributes:
        for i, layer in enumerate(layers):
            if attribute == "head" or attribute == "deprel":
                table_elements.extend(table_column(layer, attribute, deprel, text, i + 1, sentence))
            elif i == 0:
                table_elements.extend(table_column(layer, attribute, deprel, text, None, sentence))
    table_elements.append("</tr></table><button type=\"button\">save</button>")
    return "".join(table_elements)

#def one_table(layers, attributes, deprel, text):
#    tables = []
#    for i in range(len(text.sentences)):
#        tables.append(joint_table(layers, attributes, deprel, text, i))
#    return "".join(tables)

def tables(layers, attributes, deprel, text, sentence = None):
    start = 0
    end = 0
    tables = []
    for index, sentence in enumerate(text.sentences):
        start = end
        end = start + len(sentence)
        table_elements = [css(), event_handler_code(), "<table class=\"iterable-table\"><tr>"]
        for attribute in attributes:
            for i, layer in enumerate(layers):
                if attribute == "head" or attribute == "deprel":
                    table_elements.extend(table_column(layer[start:end], attribute, deprel, text, i + 1, index))
                elif i == 0:
                    table_elements.extend(table_column(layer[start:end], attribute, deprel, text, None, index))
        table_elements.append("</tr></table>")
        tables.extend(table_elements)
    tables.append("<button type=\"button\" id=\"save\">save</button><button type=\"button\" id=\"previous\">previous</button><button type=\"button\" id=\"next\">next</button>")
    return "".join(tables)