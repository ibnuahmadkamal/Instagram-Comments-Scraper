import pandas as pd
from pandas import ExcelWriter
import os.path

def export(names, comments, source_url='', fname='comments.xlsx', hidden=None):
    temp = {}
    temp_names = []
    temp_comments = []
    # if os.path.isfile(fname):
    #     saved = pd.read_excel(fname)
    #     temp_names.extend(saved['name'])
    #     temp_comments.extend(saved['comment'])
    # temp_names.extend(names)
    # temp_comments.extend(comments)
    temp.update({'name': names, 'comment': comments, 'source_url': [source_url] * len(names)})
    if hidden is not None:
        temp['hidden'] = ['yes' if h else 'no' for h in hidden]
    df = pd.DataFrame(temp)



    df.to_excel(fname)
