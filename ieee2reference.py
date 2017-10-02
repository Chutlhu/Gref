import os
import difflib
import fileinput
import sys
import pickle
import networkx   as nx
import matplotlib.pyplot as plt
import json

from glob import glob

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pybtex.database.input import bibtex

from doi_finder import google_doi
from doi_finder import crossref_auth_title_to_doi
from doi_finder import doi_lookup
from doi_finder import fuzzy_match
from habanero import Crossref

DOI_DELIMITER = "<"
map_doi_title = set()
doi_list = []

def my_save(obj, name ):
    with open('obj/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def my_load(name ):
    try:
        f = open('obj/' + name + '.pkl', 'rb')
    except:
        return None
    return pickle.load(f)

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

def check_doi(doi, title):
    lookup = doi_lookup(doi)
    try:
        return (fuzzy_match(lookup, title))
    except:
        print("    !!! Fuzzy match error:", doi, title[:40], lookup[:40])

def bibtex_to_doi(bibfile, prev_doi):
    title = bibfile.split("/")[-1].split(".")[0]
    # open a bibtex filess
    parser  = bibtex.Parser()
    bibdata = parser.parse_file(bibfile)
    # collect founded references in a dictionary {doi:title}
    item = {"doi"   : None,
            "title" : None,
            "size"  : None,
            "references": []}
    item["doi"] = prev_doi
    item["title"] = title
    item["size"] = len(bibdata.entries)
    # loop through the individual references
    print("\nExtracting DOIs and titles from: \n    %s...bib"%(bibfile[:40]))
    for bib_id in bibdata.entries:
        b = bibdata.entries[bib_id].fields
        try:
            doi   = str(b["doi"])
            title = str(b["title"])
            map_doi_title.add((doi, title))
            # if not check_doi(doi, title):
            #     print("\n    *** Fuzzy match fails for %s: \n    %s..."%(bib_id, title[0:50]))
            #     print("          pdx-extract's doi is: %s"%(doi))
            item["references"].append(prev_doi + DOI_DELIMITER + doi)
        except KeyError as e:
            print("\n    !!! Key error for %s: %s"%(bib_id, str(e)))
            continue
    # print results
    print("\n    Input bibtex db consists in:\n")
    for x in item["references"]:
        print("        " + x + "...")
    return item

def doi_to_title(doi):
    for dt in map_doi_title:
        if dt[0] == doi:
            return dt[1]
    return None


def find_by_ext(dir, ext):
    return glob(os.path.join(dir,"*%s"%ext))

def similar(seq1, seq2):
    return difflib.SequenceMatcher(a = seq1.lower(),
                                   b = seq2.lower()).ratio()

def find_best_match(target, list_of_seqs, delimiter = "_"):
    max  = 0
    for seq in list_of_seqs:
        if similar(target, seq.split(delimiter)[-1]) > max:
            max  = similar(target, seq.split("_")[-1])
            match = seq
        # print(title[0:25], path.split("_")[-1][0:25], max)
    return match

def convert_for_cmd(text):
    chars = ", "
    for c in chars:
        if c in text:
            text = text.replace(c, "\%s"%(c))
    return text

def resolve_dupes(bibfile):
    k = 0
    while True:
        try:
            parser  = bibtex.Parser()
            bibdata = parser.parse_file(bibfile)
        except Exception as e:
            err_msg = str(e)
            if "repeated" in str(err_msg):
                print(err_msg)
                # extract duplicate item name
                repreated_item = err_msg.split(":")[-1][1:]
                # Read in the file
                with open(bibfile, 'r') as file :
                    filedata = file.read()
                    # Replace the target string
                    filedata = filedata.replace(repreated_item, repreated_item + str(k), 1)
                    k += 1
                    # Write the file out again
                    with open(bibfile, 'w') as file:
                      file.write(filedata)
            else:
                print(err_msg)
                return False
            continue
        break
    print("duplicates resolved.")
    return True

def check_num_entries(bibfile):
    parser  = bibtex.Parser()
    bibdata = parser.parse_file(bibfile)
    n_bibitems = len(bibdata.entries)
    n_refs = int(raw_input("How many entries in: %s"%(bibfile)))
    if n_bibitems == n_refs:
        return True
    print("\n*** pdf-extract has found only %d entries\n"%(n_bibitems))
    return False

def pdfrefs_to_bibtexs(path_to_pdfs, title):
    pdf_filenames = find_by_ext(path_to_pdfs, '.pdf')
    # find the pdfs corresponding to the current root reference
    path_to_paper = find_best_match(title, pdf_filenames)
    if not path_to_paper:
        print("*** Paper not found: %s" %(title))
    # if not query_yes_no("Do you already extract bib manually?"):
    #     print("Skipping this paper")
    #     return None
    # # run extract-bib in the bash
    # print("\nANALIZING %s" %(path_to_paper[0:50]))
    # cmd = "pdf-extract extract-bib --resolved_references %s"%(
    #         convert_for_cmd(path_to_paper))
    # print(cmd)
    # os.system(cmd)
    # #check results and resolve dupes
    # curr_path_to_bib =  find_by_ext("./", ".bib")
    # print(curr_path_to_bib)
    # if resolve_dupes(curr_path_to_bib):
    #     if check_num_entries(bibfile):
    #         # move the file in the right folder
    #         cmd = "mv %s " + './output/'%(bash_str(curr_path_to_bib))
    #         os.system(cmd)
    #     else:
    #         print("*** Some entries are missing in: %s"%(path_to_paper))
    # else:
    #     print("*** Error in removing duplicates in: %s"%(path_to_paper))
    paper_filename = (path_to_paper.split("/")[-1]).split(".")[0]
    bib_filename = "./output/manual_bibitems/"+paper_filename+".refs.bib"
    if not os.path.isfile(bib_filename):
        print("*** file do not exists")
    return bib_filename

def pdfrefs_to_dois(path_to_pdfs, root_refs):
    child_doi_list = []
    for bib_doipath in root_refs["references"]:
        doi = bib_doipath.split("<")[-1]
        title = doi_to_title(doi)
        path_to_bibfile = pdfrefs_to_bibtexs(path_to_pdfs, title)
        child_dois = bibtex_to_doi(path_to_bibfile, bib_doipath)
        child_doi_list.append(child_dois)
    return child_doi_list

def make_ref_graph(refs):

    G = nx.DiGraph()
    node_color = []

    # scan all the references
    vertices = set()
    edges = set()
    for root_doi in refs:
        vertices.add(root_doi)
        for child_doi in refs[root_doi][1]:
            vertices.add(child_doi)
            edges.add((child_doi, root_doi))

    G.add_nodes_from(vertices)
    G.add_edges_from(edges)

    for v in G:
        if v in refs:
            node_color.append("b")
        else:
            node_color.append("r")

    nx.draw(G,
        alpha=0.5,
        node_color  = node_color,
        with_labels = True)
    plt.savefig("references_graph.png") # save as png
    plt.show() # display
    return
#
# file = "./output/Deleforge, Forbes, Horaud_2015_High-dimensional regression with gaussian mixtures and partially-latent response variables.refs.txt"
# f = open(file)
# for line in iter(f):
#     print(line)
#     auth, title = line.split("\"")[0:2]
#     # try on google
#     doi = google_doi("","","",title,auth)
#     print(" google:   ", doi)
#
#     # try on crossref
#     if not doi:
#         try:
#             cr = Crossref()
#             x = cr.works(query = title)
#             max  = 0
#             for ref in x['message']["items"]:
#                 tmp_title = ref["title"][0]
#                 if similar(title, tmp_title) > max:
#                     max  = similar(title,  tmp_title)
#                     doi =  ref["DOI"]
#                     if max < 0.9:
#                         doi = False
#             print(" crossref: ", doi)
#         except:
#             print("DOI or title not found for \n    %s \n   %s \nplease entre it manually"%(auth, title))
#             doi = raw_input("enter DOI manually: ")
#             print(" manually: ", doi)
#
#     #try manually
#         doi = raw_input("enter DOI manually: ")
#         print(" manually: ", doi)
#
#     #check doi
#     if not check_doi(doi,title):
#         print("DOI is not finded")
#         bibitem = raw_input("enter BibTex manually: ")
#         cmd = "echo " + bibitem + " "
#     else:
#         print("doi verified")
#         cmd = "curl -LH \"Accept: text/bibliography; style=bibtex\" http://dx.doi.org/" + doi
#     cmd = cmd + " >> " + file.split(" ")[0] + ".ref.bib"
#     print(cmd)
#     os.system(cmd)
# f.close()
#
# import fileinput
#
# for bibfile in find_by_ext("./output/", "bib"):
#     k = 0
#     tmp_lvl1_ref = {}
#     while True:
#         try:
#             print("ANALIZING %s" %(bibfile))
#             tmp_ref = {}
#             parser  = bibtex.Parser()
#             bibdata = parser.parse_file(bibfile)
#         except Exception as e:
#             err_msg = repreated_item)
#                 # Read in the file
#                 with open(bibfile, 'r') as file :
#                     filedata = file.read()
#                     # Replace the target string
#                     filedata = filedata.replace(repreated_item, repreated_item + str(k), 1)
#                     k += 1
#                     # Write the file out again
#                     with open(bibfile, 'w') as file:
#                       file.write(filedata)
#             continue
#         break
#     print("duplicates resolved.")
#     for bib_id in bibdata.entries:
#         b = bibdata.entries[bib_id].fields
#         try:
#             key = str(b["doi"])
#             value = str(b["title"])
#             tmp_lvl1_ref.setdefault(key,[]).append(value)
#         except KeyError as e:
#             print("*** Key error for %s: %s"%(bib_id, str(e)))
#             continue
#     lvl1_ref.setdefault(bibfile,[]).append(tmp_lvl1_ref)

def entry_exist(doi, doi_list):
    for item in doi_list:
        if item["doi"].split("<")[-1] == doi:
            return True
    return False

def add_missing_entries(doi_list):
    for level_dic in doi_list:
        for doipath in level_dic["references"]:
            for doi in doipath.split("<"):
                if not entry_exist(doi, doi_list):
                    item = {"doi"   : None,
                            "title" : None,
                            "size"  : None,
                            "references": []}
                    item["doi"]   = doi
                    item["title"] = doi_to_title(doi)
                    item["size"]  = 1
                    doi_list.append(item)
    return doi_list

if __name__ == "__main__":
    references_struct = None #my_load("references_struct")
    if not references_struct:
        root_dois  = bibtex_to_doi('./input/PhDliterature.bib', "1.1.1.1.1")
        doi_list.append(root_dois)
        child_doi_list = pdfrefs_to_dois('./input/pdfs/', root_dois)
        doi_list += child_doi_list
        doi_list = add_missing_entries(doi_list)
        with open('./output/references.json', 'w') as f:
            json.dump(doi_list, f)
        with open('./output/doi_title_map.json', 'w') as f:
            json.dump(map_doi_title, f)
        my_save(doi_list, "doi_list")
        my_save(map_doi_title, "map_doi_title")
    # make_ref_graph(references_struct)
