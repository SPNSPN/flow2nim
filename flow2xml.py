#! -*- coding: utf-8 -*-

import re
import argparse
import xml.etree.ElementTree as ET

##
#@brief mxCell内容を格納した辞書objectを文字列に変換する
#
#@param mxCell dict型
#@param indent 表示の階層
#@return 文字列
#
def print_mxCell (mxCell, indent = 0):
    cell_id = mxCell.get('id')
    cell_value = mxCell.get('value')
    ctxts = map(lambda v: print_mxCell(v, indent + 1), mxCell['children'].values())

    ans = ""
    ans += "{0}{1}\n{2}".format("  " * indent, cell_value, "\n".join(ctxts))
    return ans

##
#@brief 文字列をトークン列に分割する
#
#@param strn 変換する文字列
#@return {"type": "list", "list": <変換されたトークン列>}
#
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

##
#@brief トークン列を構文木として解釈する
#
#@param token 変換するトークン列
#
def parse_cond (token):
    #print("[DEBUG]: parse: {0}".format(token))
    stak = []
    if "list" == token["type"]:
        for e in token["list"]:
            if "atom" == e["type"]: # [TODO]: compare operator(<,>,=), numerical operator(+,-,*,/)
                if e["token"] in ["AND", "And", "and", "OR", "Or", "or", ",", "TMR", "Tmr", "tmr", "TON", "Ton", "ton"]:
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

##
#@brief 構文木を条件回路を表現するニモニックに変換する
#
#@param expr 構文木
#@param tmrlist タイマー変数の一覧
#
#@return ニモニック列, タイマー変数一覧
#
def gen_circuit (expr, tmrlist = []):
    ans = []
    if "atom" == expr["type"]:
        if expr.get("reverse"):
            ans.append(["LDI", expr["token"]])
        else:
            ans.append(["LD", expr["token"]])
    elif "ope2" == expr["type"]:
        if "," == expr["token"]:
            #ans.extend(gen_circuit(expr["arg1"]))
            rans, tmrlist = gen_circuit(expr["arg2"], tmrlist)
            ans.extend(rans)
        elif expr["token"] in ["AND", "And", "and"]:
            ans1, tmrlist = gen_circuit(expr["arg1"], tmrlist)
            ans2, tmrlist = gen_circuit(expr["arg2"], tmrlist)
            ans.extend(ans1)
            ans.extend(ans2)
            ans.append(["ANDB"])
        elif expr["token"] in ["OR", "Or", "or"]:
            ans1, tmrlist = gen_circuit(expr["arg1"], tmrlist)
            ans2, tmrlist = gen_circuit(expr["arg2"], tmrlist)
            ans.extend(ans1)
            ans.extend(ans2)
            ans.append(["ORB"])
        elif expr["token"] in ["TON", "Ton", "ton", "TMR", "Tmr", "tmr"]:
            if "atom" == expr["arg2"]["type"]:
                tans, tmrlist = gen_circuit(expr["arg1"], tmrlist)

                tmpdev = "tmp_tmr_{0}".format(len(tmrlist))
                tans.append(["TMR", expr["arg2"]["token"], tmpdev])
                tmrlist.append(tans)

                ans.append(["LD", tmpdev])
            else:
                raise RuntimeError("[ERROR]: fail TON/TMR expr: {0}".format(expr))
        else:
            raise RuntimeError("[ERROR]: unknown operator: {0}".format(expr["token"]))
    elif "list" == expr["type"]:
        for e in expr["list"]:
            rans, tmrlist = gen_circuit(e, tmrlist)
            ans.append(rans)
    else:
        raise RuntimeError("[ERROR]: cannot convert to circuit: {0}".format(expr))
    return ans, tmrlist


##
#@brief 構文木を出力回路を表現するニモニックに変換する
#
#@param expr 構文木
#
#@return ニモニック列
#
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

##
#@brief コマンドライン引数を解釈する
#
def parse_cmd_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help = "path to drawio file")
    return parser.parse_args()

##
#@brief メイン関数
#
def main (args):
    # XMLf[^Ìp[X
    root = ET.parse(args.path).getroot()

    # SÄÌmxCellðT·
    mxCells = root.findall('.//mxCell')

    # idÆvalueðoµAðÉ¶Äparentàõ
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

        # "parent"vfðT·
        if parent_id:
            id_to_mxCell[parent_id]['children'][cell_id] = id_to_mxCell[cell_id]


    # oÍ
    #print("tree: {0}".format(print_mxCell(id_to_mxCell["0"], 0)))

    # CycleÆStepðo·é
    cycle = {"no": -1, "name": ""} 
    steps = {}
    tmrlist = []
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
                if condname in ["wß"]:
                    nim.append(["LD", "Cycle{0}Step{1}Start".format(cycle["no"], step["no"])])
                    nim.append(["ANDI", "Cycle{0}Step{1}Done".format(cycle["no"], step["no"])])
                    nim.extend(gen_outcircuit(expr))
                elif condname in ["N®ð"]:
                    nim, tmrlist = gen_circuit(expr, tmrlist)
                    nim.append(["OUT", "Cycle{0}Step{1}Start".format(cycle["no"], step["no"])])
                elif condname in ["®¹ð"]:
                    nim, tmrlist = gen_circuit(expr, tmrlist)
                    nim.append(["OUT", "Cycle{0}Step{1}Done".format(cycle["no"], step["no"])])
                step[condname] = expr
                step["nim_{0}".format(condname)] = nim
            steps[step["no"]] = step 
            continue

    print("cycle: {0}".format(cycle))
    #[print("step: {0}".format(step)) for step in sorted(steps.values(), key = lambda x: x["no"])]
    [print("step[{0}]: \nN®ñH:\n{1}\nwß:\n{2}\n®¹ñH:\n{3}\n".format(step["no"], step["nim_N®ð"], step["nim_wß"], step["nim_®¹ð"])) for step in sorted(steps.values(), key = lambda x: x["no"])]
    [print("tmr: {0}".format(tmr)) for tmr in tmrlist]


if __name__ == "__main__":
    main(parse_cmd_args())

