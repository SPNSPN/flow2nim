#! -*- coding: cp932 -*-

import re
import argparse
import xml.etree.ElementTree as ET

def print_mxCell (mxCell, indent):
    cell_id = mxCell.get('id')
    cell_value = mxCell.get('value')
    ctxts = map(lambda v: print_mxCell(v, indent + 1), mxCell['children'].values())

    ans = ""
    ans += "{0}{1}\n{2}".format("  " * indent, cell_value, "\n".join(ctxts))
    return ans

def tokenize_cond (strn):
    #print("[DEBUG]: tokenize: {0}".format(strn))
    tokens = []
    tok = ""
    pindex = 0
    i = 0
    mode = "n"
    while i < len(strn):
        c = strn[i]
        #print("[DEBUG]: tokenize m: {0}, c: {1}, pidx: {2}, tok: {3}".format(mode, c, pindex, tok))
        if "n" == mode:
            if " " == c:
                if "" != tok:
                    tokens.append({"type": "atom", "token": tok})
                    tok = ""
            elif "," == c:
                if "" != tok:
                    tokens.append({"type": "atom", "token": tok})
                    tokens.append({"type": "atom", "token": ","})
                    tok = ""
            elif "(" == c:
                if "" != tok:
                    tokens.append({"type": "atom", "token": tok})
                    tok = ""
                pindex = 1
                mode = "p"
            elif ")" == c:
                raise RuntimeError("[ERROR]: too much ')' at [{0}]: \"{1}\"".format(i, strn))
            else:
                tok += c
        elif "p" == mode:
            if "(" == c:
                pindex += 1
                tok += c
            elif ")" == c:
                pindex -= 1
                if 0 == pindex:
                    #print("[DEBUG]: tokenize parensesis: {0}".format(tok))
                    tokens.append(tokenize_cond(tok))
                    tok = ""
                    mode = "n"
                else:
                    tok += c
            else:
                tok += c
        else:
            raise RuntimeError("[ERROR]: unknown mode: {0}".format(mode))
        i += 1
    if "" != tok:
        tokens.append({"type": "atom", "token": tok})
    return {"type": "list", "list": tokens}


def parse_cond (token):
    #print("[DEBUG]: parse: {0}".format(token))
    stak = []
    if "list" == token["type"]:
        for e in token["list"]:
            if "atom" == e["type"]: # [TODO]: compare operator(<,>,=), numerical operator(+,-,*,/)
                if e["token"] in ["AND", "And", "and", "OR", "Or", "or", ","]:
                    if len(stak) < 1:
                        raise RuntimeError("[ERROR]: parser got \"{0}\": requires 1/more token but stak is empty.".format(e["token"]))
                    last = stak[-1]
                    stak = stak[:-1]
                    stak.append({"type": "ope2", "token": e["token"], "arg1": last, "arg2": {"type": "atom", "token": ""}})
                elif e["token"] in ["ON", "On", "on"]:
                    pass
                elif e["token"] in ["OFF", "Off", "off"]:
                    if len(stak) < 1:
                        raise RuntimeError("[ERROR]: parser got \"{0}\": requires 1/more token but stak is empty.".format(e["token"]))
                    last = stak[-1]
                    if "atom" == last["type"]:
                        rev = last.get("reverse")
                        if rev:
                            stak[-1]["reverse"] = not rev
                        else:
                            stak[-1]["reverse"] = True
                    elif "ope2" == last["type"]:
                        rev = last["arg2"].get("reverse")
                        if rev:
                            stak[-1]["arg2"]["reverse"] = not rev
                        else:
                            stak[-1]["arg2"]["reverse"] = True
                    else:
                        stak.append(e)
                else:
                    if len(stak) < 1:
                        stak.append({"type": "atom", "token": ""})
                    last = stak[-1]
                    if "atom" == last["type"]:
                        stak[-1]["token"] += e["token"]
                    elif "list" == last["type"]:
                        stak.append(e)
                    elif "ope2" == last["type"]:
                        stak[-1]["arg2"]["token"] += e["token"]
            elif "list" == e["type"]:
                if len(stak) < 1:
                    stak.append(parse_cond(e))
                else:
                    last = stak[-1]
                    if "ope2" == last["type"]:
                        if "atom" ==  last["arg2"]["type"] and "" == last["arg2"]["token"]:
                            stak[-1]["arg2"] = parse_cond(e)
                        else:
                            raise RuntimeError("[ERROR]: syntax error ope2(\"{0}\") got 3/more args: {1}, at \"{2}\"".format(last["token"], e, strn))
                    else:
                        stak.append(parse_cond(e))
            else:
                raise RuntimeError("[ERROR]: unknown token: {0}".format(e))
        if len(stak) < 1:
            stak.append({"type": "list", "list": []})
    elif "atom" == token["type"]:
        stak.append(token)
    else:
        raise RuntimeError("[ERROR]: unknown token: {0}".format(token))
    if len(stak) != 1:
        print("[WARN]: too much tokens: {0}".format(stak))
    return stak[-1]


def gen_circuit (expr):
    ans = []
    if "atom" == expr["type"]:
        if expr.get("reverse"):
            ans.append(["LDI", expr["token"]])
        else:
            ans.append(["LD", expr["token"]])
    elif "ope2" == expr["type"]:
        if "," == expr["token"]:
            #ans.extend(gen_circuit(expr["arg1"]))
            ans.extend(gen_circuit(expr["arg2"]))
        elif expr["token"] in ["AND", "And", "and"]:
            ans.extend(gen_circuit(expr["arg1"]))
            ans.extend(gen_circuit(expr["arg2"]))
            ans.append(["ANDB"])
        elif expr["token"] in ["OR", "Or", "or"]:
            ans.extend(gen_circuit(expr["arg1"]))
            ans.extend(gen_circuit(expr["arg2"]))
            ans.append(["ORB"])
        else:
            raise RuntimeError("[ERROR]: unknown operator: {0}".format(expr["token"]))
    elif "list" == expr["type"]:
        for e in expr["list"]:
            ans.append(gen_circuit(e))
    else:
        raise RuntimeError("[ERROR]: cannot convert to circuit: {0}".format(expr))
    return ans

def gen_outcircuit (expr):
    ans = []
    if "atom" == expr["type"]:
        ans.append(["OUT", expr["token"]])
    elif "ope2" == expr["type"]:
        if "," == expr["token"]:
            ans.append(["PUSH"])
            ans.extend(gen_outcircuit(expr["arg1"]))
            ans.append(["POP"])
            ans.extend(gen_outcircuit(expr["arg2"]))
        else:
            raise RuntimeError("[ERROR]: cannot convert ope2 to outcircuit: {0}".format(expr))
    elif "list" == expr["type"]:
        for e in expr["list"]:
            ans.append(gen_outcircuit(e))
    else:
        raise RuntimeError("[ERROR]: cannot type to outcircuit: {0}".format(expr))
    return ans

def parse_cmd_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help = "path to drawio file")
    return parser.parse_args()

def main (args):
    # XMLデータのパース
    root = ET.parse(args.path).getroot()

    # 全てのmxCellを探す
    mxCells = root.findall('.//mxCell')

    # idとvalueを抽出し、条件に応じてparentも検索
    id_to_mxCell = {}
    for cell in mxCells:
        cell_id = cell.get("id")
        cell_value = cell.get("value")
        if cell_value:
            cell_value = cell_value.replace("<div>", " ").replace("</div>", " ")
        id_to_mxCell[cell_id] = {"id": cell_id,
                "value": cell_value,
                "parent": cell.get("parent"),
                "children": {}}

    for cell in mxCells:
        cell_id = cell.get('id')
        cell_value = cell.get('value', '')
        parent_id = cell.get('parent')

        # "parent"要素を探す
        if parent_id:
            id_to_mxCell[parent_id]['children'][cell_id] = id_to_mxCell[cell_id]


    # 出力
    #print("tree: {0}".format(print_mxCell(id_to_mxCell["0"], 0)))

    # CycleとStepを抽出する
    cycle = {"no": -1, "name": ""} 
    steps = {}
    for c in id_to_mxCell["1"]["children"].values():
        val = c["value"]
        if not val:
            continue
        m = re.match("\[?(Cycle|cycle|CYCLE)([0-9]+)\]?(.*)$", val)
        if m: # Cycle
            cycle["no"] = m[2]
            cycle["name"] = m[3]
            for cc in c["children"].values():
                ccc = sorted(cc["children"].values(), key = lambda x: x["id"])
                tokens = tokenize_cond(ccc[1]["value"])
                expr = parse_cond(tokens)
                cycle[ccc[0]["value"]] = expr
            continue
        m = re.match("\[?(Step|step|STEP)([0-9]+)\]?(.*)$", val)
        if m: # Step
            step = {}
            step["no"] = m[2]
            step["name"] = m[3]
            for cc in c["children"].values():
                ccc = sorted(cc["children"].values(), key = lambda x: x["id"])
                tokens = tokenize_cond(ccc[1]["value"])
                condname = ccc[0]["value"]
                expr = parse_cond(tokens)
                nim = []
                if condname in ["指令"]:
                    nim.append(["LD", "Cycle{0}Step{1}Start".format(cycle["no"], step["no"])])
                    nim.append(["ANDI", "Cycle{0}Step{1}Done".format(cycle["no"], step["no"])])
                    nim.extend(gen_outcircuit(expr))
                elif condname in ["起動条件"]:
                    nim = gen_circuit(expr)
                    nim.append(["OUT", "Cycle{0}Step{1}Start".format(cycle["no"], step["no"])])
                elif condname in ["完了条件"]:
                    nim = gen_circuit(expr)
                    nim.append(["OUT", "Cycle{0}Step{1}Done".format(cycle["no"], step["no"])])
                step[condname] = expr
                step["nim_{0}".format(condname)] = nim
            steps[step["no"]] = step 
            continue

    print("cycle: {0}".format(cycle))
    #[print("step: {0}".format(step)) for step in sorted(steps.values(), key = lambda x: x["no"])]
    [print("step[{0}]: \n起動回路:\n{1}\n指令:\n{2}\n完了回路:\n{3}\n".format(step["no"], step["nim_起動条件"], step["nim_指令"], step["nim_完了条件"])) for step in sorted(steps.values(), key = lambda x: x["no"])]


if __name__ == "__main__":
    main(parse_cmd_args())

