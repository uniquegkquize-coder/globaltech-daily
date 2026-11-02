"""Readable, source-grounded search descriptions for current and legacy posts."""
import ast
import html
import json
import re


def plain(value):
    value=re.sub(r'\[([^\]]+)\]\(https?://[^\s)]+\)',r'\1',str(value))
    value=re.sub(r'https?://\S+','',value)
    value=re.sub(r'<[^>]+>',' ',value)
    return re.sub(r'\s+',' ',html.unescape(value).replace('**','').replace('`','')).strip()


def readable(value,depth=0):
    if depth>3:return ''
    if isinstance(value,dict):
        keys={str(k).lower():v for k,v in value.items()}
        for key in ('description','meta_description','meta','summary'):
            result=readable(keys.get(key),depth+1)
            if result:return result
        return ''
    if not isinstance(value,str):return ''
    value=value.strip()
    if value.startswith(('{','[')):
        if len(value)>12000:return ''
        for decoder in (json.loads,ast.literal_eval):
            try:return readable(decoder(value),depth+1)
            except (ValueError,SyntaxError,TypeError,RecursionError):pass
        return ''
    return plain(value)


def description(value,body='',title='',limit=160):
    result=readable(value)
    if not result:
        for paragraph in re.split(r'\n\s*\n',str(body)):
            paragraph=paragraph.strip()
            if not paragraph or paragraph.startswith(('#','- ','* ','---','{','[')):continue
            result=readable(paragraph)
            if result:break
    result=result or readable(title)
    if len(result)>limit:
        cut=result[:limit-1]
        if ' ' in cut:cut=cut.rsplit(' ',1)[0]
        result=cut.rstrip(' ,;:')+'…'
    return result
