
query_parts = []

mapp = {"multiply":"*","add":"+","sub":"-","greater_than":">","lesser_than":"<","equal_to":"=",'greater_than_or_equal':">=",'lesser_than_or_equal':"<=","in":"in","is in":"is in","not in":"not in","is null":"is null","is not null":"is not null","between":"between","AND":"AND","OR":"OR"}

def convert(data):
    return tuple(int(item) if item.isdigit() else float(item) if item.replace(".", "", 1).isdigit() else item for item in data)

def generate_function(seq, column,column2=None,cast=None):
    if len(seq) == 1:
        if column and type(column)==dict:
            if 'left_operand' in column:
                column = getQ(column)
            elif 'when' in column:
                column = whOt([column])[0]
        if column2 and type(column2)==dict:
            if 'left_operand' in column2:
                column2 = getQ(column2)
            elif 'when' in column2:
                column2 = whOt([column2])[0]
        return f"{seq[0]}({column}{',' + column2 if column2 else ''}{' as '+cast if cast else ''})"
    else:
        return f"{seq[0]}({generate_function(seq[1:], column,column2,cast)})"
    
def getQ(d):
    if type(d['left_operand'])==dict:
        if "function" in d['left_operand']:
            d['left_operand'] = generate_function(
                                    d['left_operand']['function'].split(","),
                                    d['left_operand']['column'],
                                    d['left_operand'].get('column2'),
                                    d['left_operand'].get('cast'))
        elif "left_operand" in d["left_operand"]:
            d['left_operand'] = getQ(d['left_operand'])
        elif "query" in d["left_operand"]:
            d['left_operand'] = "("+generateQuery(d["left_operand"])+")"
        else:
            d['left_operand'] = d['left_operand']['column']
    if (('right_operand' in d) and (type(d['right_operand'])==dict)):
        if "function" in d['right_operand']:
            d['right_operand'] = generate_function(
                                    d['right_operand']['function'].split(","),
                                    d['right_operand']['column'],
                                    d['right_operand'].get('column2'),
                                    d['right_operand'].get('cast'))
        elif "right_operand" in d["right_operand"]:
            d['right_operand'] = getQ(d['right_operand'])
        elif "query" in d["right_operand"]:
            d['right_operand'] = "("+generateQuery(d["right_operand"])+")"
        else:
            d['right_operand'] = d['right_operand']['column']
        # return f"({d['left_operand']} {mapp[d['operator']]} {d['right_operand']})"
    elif 'right_operand' in d:
        if "," in d['right_operand']:
            x = convert(d['right_operand'].split(",")) if d['operator']!='between' else d['right_operand'].replace(","," and ")
            d['right_operand'] = x
            return f"({d['left_operand']} {mapp[d['operator']]} {d['right_operand']})"
        if (x:=convert([d['right_operand']])[0])!=d['right_operand']:
            return f"({d['left_operand']} {mapp[d['operator']]} {x})"
        if mapp[d['operator']] in ['in','not in']:
            return f"({d['left_operand']} {mapp[d['operator']]} ('{d['right_operand']}'))" 
        if "." in d['right_operand']:
            return f"({d['left_operand']} {mapp[d['operator']]} {d['right_operand']})"
        return f"({d['left_operand']} {mapp[d['operator']]} '{d['right_operand']}')"
    return f"({d['left_operand']} {mapp[d['operator']]} {d['right_operand'] if 'right_operand' in d else ''})"

def whOt(data):
    query_parts = []
    for ind_cond in data:
        name = ind_cond.get("name")
        conditions = ind_cond["when"]
        otherwise = ind_cond["otherwise"]

        query_part = f"CASE "
        condition_parts = []
        for condition in conditions:
            qp = f"WHEN ("
            for i in condition["condition"]:
                qp += f" {i['op']} " if 'op' in i else getQ(i)
            value = condition["value"]
            value = value["value"] if "value" in value else (generate_function(value['function'].split(","),value['column'],value.get('column2'),value.get('cast')) if 'function' in value else f"({generateQuery(value['column'])})")
            qp += f") THEN {value} "
            condition_parts.append(qp)
        query_part += "".join(condition_parts)
        end = f"ELSE {otherwise} END AS {name}" if name else f"ELSE {otherwise} END "
        query_part += end
        query_parts.append(query_part)
    return query_parts

def generateAgg(data):
    query_parts=[]
    for agg in data:
        if 'when' in agg:
            aggcpy = agg.copy()
            del aggcpy['name']
            query = whOt([aggcpy])[0]
            # query_parts.append(f", {agg['function']}({(query)}) AS {agg['name']}")
            if 'name' in agg:
                query_parts.append(f" {generate_function(agg['function'].split(','),query,None,None)}  {'AS '+agg['name'] if 'name' in agg else ''}")
            else:
                query_parts.append(f" {generate_function(agg['function'].split(','),query,None,None)} ")
        else:
            query = generate_function([agg['function']],agg['column'],agg.get('column2'),agg.get('cast'))
            # query_parts.append(f" {query} AS {agg['name']}")
            query_parts.append(f" {query} {'AS '+agg['name'] if 'name' in agg else ''}")
    return query_parts

def generateSelect(data):
    data = [f"( {generateQuery(d)}) {'AS '+d['name'] if 'name' in d else ''}" if type(d)==dict else d for d in data]
    return f"SELECT {', '.join(data)}"

def generateWithColumn(data):
    query_parts = []
    for with_column in data:
        name = with_column['name']
        wcexp = with_column['expression']
        if type(wcexp)==dict:
            if "when" in wcexp:
                wcexp = whOt([wcexp])[0]
            elif "function" in wcexp:
                wcexp = generate_function([wcexp['function']],wcexp['column'],wcexp.get("column2"),wcexp.get("cast"))
        if 'cast' in with_column:
            wcexp = generate_function(['cast'],wcexp,None,"bigint")
        query_parts.append(f"{wcexp} AS {name}")
    return query_parts

def generateSelectJoin(data):
    part = []
    for i in data:
        part += [i+"."+clm for clm in data[i].split(",")]
    return "SELECT "+", ".join(part)
def generateOnJoin(data):
    data = [i.split(",") for i in data]
    part = f" FROM {data[0][0]}"
    for item in data:
        part += f" {item[2]} {item[3]} ON {item[0]}.{item[1]} = {item[3]}.{item[4]}"
    return part

def generateQuery(cfig):
    allQuery = []
    for qryNo,qry in enumerate(cfig['query']):
        flg = 0
        finalQuery = ""
        grpBy = ""
        if 'select' in qry:
            finalQuery += generateSelect(qry['select'])
            grpBy = f" group by {','.join([s for s in qry['select'] if type(s)!=dict ])}"
            flg = 1
        for uc in qry:
            if uc=='withColumn':
                finalQuery += f"{',' if flg else 'SELECT '}"+", ".join(generateWithColumn(qry['withColumn']))
                flg = 1
            elif uc=="caseWhen":
                finalQuery += f"{',' if flg else 'SELECT '}"+whOt(qry['caseWhen'])[0]
                flg = 1
            elif uc=="agg":
                finalQuery += f"{',' if flg else 'SELECT '}"+",".join(generateAgg(qry['agg']))
                flg = 1
        if "from" in qry:
                finalQuery += f" from {qry['from']} "
        if "filter" in qry:
            qp = " where "
            for i in qry['filter']:
                qp += f" {i['op']} " if 'op' in i else getQ(i)
            finalQuery += qp
        finalQuery += grpBy
        if 'name' in qry:
            allQuery.append(f"{'WITH' if not qryNo else ''} {qry['name']} AS ({finalQuery}) ")
        else:
            allQuery.append(finalQuery)
    if 'join' in cfig:
        res1 = generateSelectJoin(cfig['join']['colsToSelect'])
        res2 = generateOnJoin(cfig['join']['colsToJoin'])
        return ",".join(allQuery)+res1+res2
    else:
        return allQuery[0]