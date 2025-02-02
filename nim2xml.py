#! -*- coding: cp932 -*-

import json
import argparse



def parse_cmd_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help = "path to nim.json")
    parser.add_argument("--enc", default = "shift_jis", help = "encoding of nim.json")
    return parser.parse_args()

def main (args):
    data = None
    with open(args.path, "r", encoding = args.enc) as f:
        data = json.load(f)

    rungs = []
    stak = []
    lin = []
    cnt = 0
    ref = []
    for ope in data["body"]:
        if not ope.get("operation"):
            continue
        if int(ope["operation"]) < 1:
            continue

        if len(lin) < 1:
            lin = [[{"type": "left", "device": "", "id": 1, "in": []}]]
            cnt = 2

        devs = ope["devices"]
        #print("[DEBUG]: devs: {0}, ref: {1}".format(devs, ref))
        if "LD" == devs[0]:
            stak.append(lin)
            obj = {"type": "contact", "device": devs[1], "id": cnt, "in": []}
            lin = [[obj]]
            ref = lin[-1]
            cnt += 1
        elif "AND" == devs[0]:
            obj = {"type": "contact", "device": devs[1], "id": cnt, "in": [e["id"] for e in ref]}
            lin.append([obj])
            ref = lin[-1]
            cnt += 1
        elif "OR" == devs[0]:
            obj = {"type": "contact", "device": devs[1], "id": cnt, "in": ref[0]["in"]}
            lin[-1].append(obj)
            ref = lin[-1]
            cnt += 1
        elif "ANL" == devs[0]:
            p = stak[-1]
            stak = stak[:-1]
            for l0 in lin[0]:
                l0["in"] = [pl["id"] for pl in p[-1]]
            lin = p + lin
            ref = lin[-1]
        elif "ORL" == devs[0]:
# p = [[a], [b], [c]], lin = [[d], [e], [f]]
# -> lin = [[a, d], [b], [e], [c, f]]
            p = stak[-1]
            stak = stak[:-1]
#            for l0 in lin[0]:
#                l0["in"] = p[0][0]["in"] 
#            lin[-1].extend(p[-1])
#            objs = lin[0]
#            lin = p[:-1] + lin[1:]
#            lin[0].extend(objs)

            nlin = [p[0] + lin[0]]
            nlin.extend(p[1:-1])
            nlin.extend(lin[1:-1])
            nlin.append(p[-1] + lin[-1])
            ref = nlin[-1]
            lin = nlin
        elif "MOV" == devs[0]:
# lin = [[a], [b], [c]]
# nlin = [[a], [b], [c], [DataSource id=c], [DataSink id=c+1], [FbdObject MOV id=c+2]]
            srcid = cnt
            sinkid = cnt + 1
            src = {"type": "DataSource", "device": devs[1], "id": srcid, "in": [1]}
            sink = {"type": "DataSink", "device": devs[2], "id": sinkid, "in": []}

            fbdid = cnt + 2
            fbdin = [e["id"] for e in ref]
            fbd = {"type": "FbdObject", "device": "MOV",
                "id": fbdid, "in": fbdin,
                "inputs": [["EN", fbdin], ["In1", [srcid]]], "outputs": [["ENO", fbdid], ["Out1", sinkid]]}

            lin += [[src], [sink], [fbd]]
            ref = lin[-1]
            cnt += 3

            if len(stak) == 1:
                for l0 in lin[0]:
                    l0["in"] = [stak[-1][-1][0]["id"]]
                rungs.append(stak[-1] + lin + [[{"type": "right", "device": "", "id": cnt, "in": [e["id"] for e in lin[-1]]}]])
                stak = []
                lin = []
                cnt = 0
                ref = []

        elif "MPS" == devs[0]:
            stak.append([ref])
        elif "MPP" == devs[0]:
            p = stak[-1]
            stak = stak[:-1]
            ref = p[-1]
        elif "OUT" == devs[0]:
            obj = {"type": "coil", "device": devs[1], "id": cnt, "in": [e["id"] for e in ref]}
            lin.append([obj])
            ref = lin[-2]
            cnt += 1

            if len(stak) == 1:
                for l0 in lin[0]:
                    l0["in"] = [stak[-1][-1][0]["id"]]
                rungs.append(stak[-1] + lin + [[{"type": "right", "device": "", "id": cnt, "in": [e["id"] for e in lin[-1]]}]])
                stak = []
                lin = []
                cnt = 0
                ref = []
        else:
            raise RuntimeError("[ERROR]: Unknown ope: {0}".format(devs))
    print(json.dumps(rungs, indent = 4))

if __name__ == "__main__":
    main(parse_cmd_args())

