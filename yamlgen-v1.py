import subprocess
subprocess.call(['./setup.sh'], shell=True)

import streamlit as st
import yaml
from ds_final import generateQuery

if 'yaml_data' not in st.session_state:
    st.session_state.yaml_data = {"query": [],"subquery":dict()}
    st.session_state.query_data = dict()

if 'when_condition' not in st.session_state:
    st.session_state.when_condition = {'condition':[],'value':{"value":None}}   

if 'sql' not in st.session_state:
    st.session_state.sql = None
    st.session_state.queryFile = 0

def process_subquery(data,nameNeed=False):
    res = dict()
    if nameNeed:
        res["name"] = data["name"]
    res["query"] = [{**data}]
    res["query"][0].pop("name")
    return res

def add_select_element(qsj):
    selected_columns = st.text_area("Selected Columns (comma-separated)",key=qsj+'sc')
    subquerySelected = []
    if qsj=="query":
        subquerySelected = st.multiselect("SubQuery",options=st.session_state.yaml_data['subquery'].keys())
    if st.button("Add To YAML",key=qsj+'btn'):
        if 'select' not in st.session_state.query_data:
            st.session_state.query_data['select'] = []
        if subquerySelected:
            st.session_state.query_data['select'].extend([process_subquery(st.session_state.yaml_data["subquery"][sq],nameNeed=True) for sq in subquerySelected])
        st.session_state.query_data['select'].extend([col.strip() for col in selected_columns.split(",")])
        st.rerun()
    return st.session_state.query_data


def add_operand(operand_name,keyInd): 
    operand_type = st.radio(f"{operand_name} Operand Type", ["Value", "Function-Column","LeftOp-Op-RightOp","SubQuery"],key=f"{keyInd}_ot",horizontal=True)
    if operand_type == "Value":
        operand_value = st.text_input(f"{operand_name} Operand Value",key=f"{keyInd}_ov")
        return operand_value
    elif operand_type == "Function-Column":
        operand_function, operand_column ,operand_column2, operand_cast = add_function_operands(operand_name,keyInd)
        res = {
            "function": operand_function,
            "column": operand_column
        }
        if operand_column2:
            res["column2"] = operand_column2
        if operand_cast:
            res["cast"] = operand_cast
        return res

    elif operand_type == "SubQuery":
        subquerySelected = st.selectbox("SubQuery",options=st.session_state.yaml_data['subquery'].keys(),key=f"{keyInd}_sq")
        return process_subquery(st.session_state.yaml_data["subquery"][subquerySelected])

    elif operand_type == "LeftOp-Op-RightOp":
        left_operand, operator, right_operand = add_condition_operands(keyInd)
        return {
                "left_operand": left_operand,
                "operator": operator,
                "right_operand": right_operand
            }

def add_function_operands(operand_name,keyInd):
    operand_function = st.text_input(f"{operand_name} Operand Function",key=f"{keyInd}_of")
    operand_cast = st.selectbox(f"{operand_name} Operand Cast (Optional)",options=["int","bigint","float","double","long"],index=None,key=f"{keyInd}_ct")
    column_type = st.radio("Column Type",["Column Value","LeftOp-Op-RightOp"],horizontal=True,key=f"{keyInd}_colt")
    operand_column = None
    operand_column2 = None
    if column_type=="Column Value":
        operand_column = st.text_input(f"{operand_name} Operand Column",key=f"{keyInd}_oc")
    elif column_type=="LeftOp-Op-RightOp":
        operand_column = add_operand(operand_name,keyInd+'c')
    column_type2 = st.radio("Column2 Type",["None","Column2 Value","LeftOp-Op-RightOp"],horizontal=True,key=f"{keyInd}_ct2")
    if column_type2=="Column2 Value":
        operand_column2 = st.text_input(f"{operand_name} Operand Column2",key=f"{keyInd}_oc2")
    elif column_type2=="LeftOp-Op-RightOp":
        operand_column2 = add_operand(operand_name,keyInd+'c2')
    return operand_function, operand_column ,operand_column2, operand_cast


def add_condition_operands(keyInd):
    with st.container():
        left_operand = add_operand(f"Left",keyInd+'l')
        operator = st.selectbox("Operator", ["multiply","add","sub","greater_than","lesser_than","equal_to","greater_than_or_equal","lesser_than_or_equal","in","is in","not in","is null","is not null","between","AND","OR"],key=f"{keyInd}_op")
        right_operand = add_operand(f"Right",keyInd+'r')
    return left_operand, operator, right_operand


def add_when_condition(qsj):
    if 'when_condition' not in st.session_state:
        st.session_state.when_condition = {'condition':[],'value':{"value":None}}
    keyInd = qsj+'I'
    slcted = st.radio("ConditionType",["LeftOp-Op-RightOp","Operator"],horizontal=True)
    if slcted=="LeftOp-Op-RightOp":
        left_operand, operator, right_operand = add_condition_operands(keyInd)
        
        if st.button("AddConditionToList"):
            st.session_state.when_condition["condition"].append({
            "left_operand": left_operand,
            "operator": operator,
            "right_operand": right_operand
        })
        value = st.text_input("Value for When")
        st.session_state.when_condition["value"]["value"] = value
        return st.session_state.when_condition
    else:
        slcted = st.selectbox("Op",["AND","OR"])
        if st.button("AddOpToList"):
            st.session_state.when_condition["condition"].append({
                "op":slcted
            })
            return st.session_state.when_condition



def add_withColumn_element(qsj):
    with_column_name = st.text_input("Column Name",key=qsj+"wcn")
    expression_type = st.radio("Expression Type", ["Normal", "When-Otherwise","Function-Column"],horizontal=True,key=qsj+"et")
    if expression_type == "Normal":
        with_column_expression = st.text_input("Expression",key=qsj+"exp")
        with_column_data = {
            'name': with_column_name,
            'expression': with_column_expression,
        }
    elif expression_type == "When-Otherwise":
        # when_conditions = []
        # when_condition = add_when_condition()
        # when_conditions.append(when_condition)
        add_when_condition(qsj)
        otherwise = st.text_input("Otherwise Value",key=qsj+"ov")
        with_column_data = {
            'name': with_column_name,
            'expression': {
                "when": [st.session_state.when_condition],
                "otherwise": otherwise
            },
        }
    else:
        operand_function, operand_column ,operand_column2, operand_cast = add_function_operands("",qsj+"f")
        with_column_data = {
            'name': with_column_name,
            'expression': {
                'function' : operand_function,
                'column' : operand_column
            }
        }
        if operand_column2:
            with_column_data['expression']["column2"] = operand_column2
        if operand_cast:
            with_column_data['expression']["cast"] = operand_cast

    with_column_cast = st.selectbox("Cast (optional)",options=["int","bigint","float","double","long"],index=None)
    if with_column_cast:
        with_column_data['cast'] = with_column_cast
    if st.button("Add To YAML"):
        if 'withColumn' not in st.session_state.query_data:
            st.session_state.query_data['withColumn'] = []
        st.session_state.when_condition = {'condition':[],'value':{"value":None}}
        existing_entry_index = None
        for index,wc in enumerate(st.session_state.query_data['withColumn']):
            if wc["name"] == with_column_name:
                existing_entry_index = index
                break
        if existing_entry_index is not None:
            st.session_state.query_data['withColumn'][existing_entry_index]['expression']['when'].extend(with_column_data['expression']['when'])
        else:
            st.session_state.query_data['withColumn'].append(with_column_data)        
        st.rerun()
    return st.session_state.query_data

def add_agg_element(qsj):
    agg_column_name = st.text_input("New Column Name",key=qsj+"acn")
    agg_function = ",".join(st.multiselect("Agg Function",["sum","count","min","max","avg"],key=qsj+"af"))
    agg_column_data = {
        "name" : agg_column_name,
        "function" : agg_function,
    }
    column_type = st.radio("Column Type", ["Column Value", "When-Otherwise"],horizontal=True,key=qsj+"act")
    if column_type == "Column Value":
        column_value = st.text_input("column name",key=qsj+"acv")
        agg_column_data['column'] = column_value
    elif column_type == "When-Otherwise":
        add_when_condition()
        otherwise = st.text_input("Otherwise Value",key=qsj+"aov")
        agg_column_data['when'] = [st.session_state.when_condition]
        agg_column_data["otherwise"] = otherwise
    
    if st.button("Add To YAML"):
        if 'agg' not in st.session_state.query_data:
            st.session_state.query_data['agg'] = []
        st.session_state.when_condition = {'condition':[],'value':{"value":None}}
        existing_entry_index = None
        for index,wc in enumerate(st.session_state.query_data['agg']):
            if wc["name"] == agg_column_name:
                existing_entry_index = index
                break
        if existing_entry_index is not None:
            st.session_state.query_data['agg'][existing_entry_index]['when'].extend(agg_column_data['when'])
        else:
            st.session_state.query_data['agg'].append(agg_column_data)        
        st.rerun()
    return st.session_state.query_data

def add_casewhen_element(qsj):
    casewhen_column_name = st.text_input("New Column Name",key=qsj+"cwcn")
    add_when_condition(qsj)
    otherwise = st.text_input("Otherwise Value",key=qsj+"cwo")
    casewhen_column_data = {
        'name' : casewhen_column_name,
        'when' : [st.session_state.when_condition],
        'otherwise' : otherwise
    }
    if st.button("Add To YAML"):        
        if 'caseWhen' not in st.session_state.query_data:
            st.session_state.query_data['caseWhen'] = []
        st.session_state.when_condition = {'condition':[],'value':{"value":None}}
        existing_entry_index = None
        for index,wc in enumerate(st.session_state.query_data['caseWhen']):
            if wc["name"] == casewhen_column_name:
                existing_entry_index = index
                break
        if existing_entry_index is not None:
            st.session_state.query_data['caseWhen'][existing_entry_index]['when'].extend(casewhen_column_data['when'])
        else:
            st.session_state.query_data['caseWhen'].append(casewhen_column_data)        
        st.rerun()
    return st.session_state.query_data

def add_from_element(qsj):
    from_data = st.text_input("Table Name",key=qsj+'tn')
    if qsj=="subquery":
        subqueryName = st.text_input("name for subquery",key=qsj+'sn')
    if st.button("Add Table",key=qsj+'table'):        
        if 'from' not in st.session_state.query_data:
            st.session_state.query_data['from'] = None
        st.session_state.query_data['from'] = from_data
        if qsj=="query":
            st.session_state.query_data['name'] = "table_"+from_data
            st.session_state.yaml_data['query'].append(st.session_state.query_data)
        else:
            st.session_state.query_data['name'] = subqueryName
            st.session_state.yaml_data['subquery'][subqueryName] = st.session_state.query_data
        st.session_state.query_data = dict()
        st.rerun()
    return st.session_state.query_data

def add_filter_element(qsj):
    keyInd = qsj+'F'
    slcted = st.radio("ConditionType",["LeftOp-Op-RightOp","Operator"],horizontal=True,key=qsj+"filter")
    if slcted=="LeftOp-Op-RightOp":
        left_operand, operator, right_operand = add_condition_operands(keyInd)
        res = {
            "left_operand": left_operand,
            "operator": operator,
            "right_operand": right_operand
        }
    else:
        Op = st.selectbox("Op",["AND","OR"])
        res = {'op':Op}

    if st.button("Add Filter To YAML"):
        if 'filter' not in st.session_state.query_data:
            st.session_state.query_data['filter'] = []
        st.session_state.query_data['filter'].append(res)
        st.rerun()
    return st.session_state.query_data

def colsToSelect():
    allColumns = dict()
    for qry in st.session_state.yaml_data["query"]:
        allColumns[qry['name']] = []
        for element in qry:
            if element not in ["from","name"]:
                allColumns[qry['name']].extend([e['name'] if type(e)==dict else e for e in qry[element]])
    selectColumns = dict()
    for k,v in allColumns.items():
        slcted = st.multiselect(k,v)
        if slcted:
            selectColumns[k] = ",".join(slcted)
    if st.button("Add Selected Columns"):
        st.session_state.yaml_data['join'] = dict()
        if "colsToSelect" not in st.session_state.yaml_data['join']:
            st.session_state.yaml_data['join']["colsToSelect"] = {}
        st.session_state.yaml_data['join']["colsToSelect"] = selectColumns
    return st.session_state.yaml_data
    
def colsToJoin():
    allColumns = dict()
    for qry in st.session_state.yaml_data["query"]:
        allColumns[qry['name']] = []
        for element in qry:
            if element not in ["from","name"]:
                allColumns[qry['name']].extend([e['name'] if type(e)==dict else e for e in qry[element]])
    if allColumns:
        t1,c1,j,t2,c2 = st.columns(5)
        with t1:
            t1s = st.selectbox("Left Table",options=allColumns.keys())
        with c1:
            c1s = st.selectbox("Left Column",[*allColumns[t1s]])
        with j:
            js = st.selectbox("Join",["LeftJoin","Join","RightJoin"])
        with t2:
            t2s = st.selectbox("Right Table",options=allColumns.keys())
        with c2:
            c2s = st.selectbox("Right Column",[*allColumns[t2s]])
        
        if st.button("Add Join Condition"):
            if "colsToJoin" not in st.session_state.yaml_data['join']:
                st.session_state.yaml_data['join']["colsToJoin"] = []
            st.session_state.yaml_data['join']["colsToJoin"].append(f"{t1s},{c1s},{js},{t2s},{c2s}")
    return st.session_state.yaml_data

def main(qsj):
    ElementSelected = st.selectbox("Query Elements", ["select", "withColumn", "Aggregation", "caseWhen", "filter"],index=None,key=qsj)
    if ElementSelected == 'select':
        st.session_state.query_data = add_select_element(qsj)
    elif ElementSelected == 'withColumn':
        st.session_state.query_data = add_withColumn_element(qsj)
    elif ElementSelected == 'Aggregation':
        st.session_state.query_data = add_agg_element(qsj)
    elif ElementSelected == 'caseWhen':
        st.session_state.query_data = add_casewhen_element(qsj)
    elif ElementSelected == 'filter':
        st.session_state.query_data = add_filter_element(qsj)
    st.divider()
    st.session_state.query_data = add_from_element(qsj)
    return st.session_state.query_data


st.sidebar.write("YAML Data",st.session_state.yaml_data)
st.sidebar.write("QUERY Data",st.session_state.query_data)
st.sidebar.divider()
st.sidebar.write("Conditions Temporary",st.session_state.when_condition)

tab1,tab2,tab3 = st.tabs(["query","subquery","Join"])

with tab1:
    st.session_state.query_data = main("query")
    col1,col2,col3 = st.columns(3)
    with col1:
        st.download_button(
            label="Download YAML",
            data=yaml.dump(st.session_state.yaml_data),
            key="yaml_download",
            file_name="data.yaml",
            mime="text/yaml",
        )
    with col2:
        if st.button("Generate SQL Query"):
            yaml_data_1 = st.session_state.yaml_data
            if ((len(yaml_data_1['query'])==1) or ('join' not in yaml_data_1)) and "name" in yaml_data_1["query"][0]:
                del yaml_data_1["query"][0]["name"]
            config = yaml.safe_load(yaml.dump(yaml_data_1))
            st.session_state.sql=generateQuery(config)
            st.session_state.queryFile+=1
            with open(f"generated_sql{st.session_state.queryFile}.txt","w") as file:
                file.write(st.session_state.sql)
    with col3:
        if st.button("Run SQL Query"):
            
            command = f"spark-submit --master local[*] feature_generator.py --queryFile generated_sql{st.session_state.queryFile}.txt"
            try:
                subprocess.run(command, shell=True, check=True)
                st.success("Spark job ran successfully!")
            except subprocess.CalledProcessError as e:
                st.error(f"Error running Spark job: {e}")

    if st.session_state.sql:
        st.code(st.session_state.sql,language="sql")

with tab2:
    st.session_state.query_data = main("subquery")

with tab3:
    if len(st.session_state.yaml_data['query'])>1:
        st.session_state.yaml_data = colsToSelect()
        st.session_state.yaml_data = colsToJoin()
    else:
        st.text("Only One Table Added")
