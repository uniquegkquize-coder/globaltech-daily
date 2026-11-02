import ast
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect

class PublishingEfficiencyTests(unittest.TestCase):
 def test_new_story_uses_one_call_for_both_languages(self):
  response={'en':{'title':'English title','body':'English body'},'hi':{'title':'हिन्दी शीर्षक','body':'हिन्दी लेख'}}
  with patch.object(collect,'call_provider',return_value=(response,'gemini')) as call:
   rows=collect.generate_story_languages({},'Title','https://example.org','Evidence','technology',['en','hi'])
  self.assertEqual(call.call_count,1)
  self.assertEqual(rows[0][1],response['en']);self.assertEqual(rows[1][1],response['hi'])
 def test_saved_english_only_generates_missing_hindi(self):
  with patch.object(collect,'call_provider',return_value=({'body':'Hindi'},'gemini')) as call:
   rows=collect.generate_story_languages({'en_body':'Saved'},'Title','https://example.org','Evidence','technology',['hi'])
  self.assertEqual(call.call_count,1);self.assertEqual([r[0] for r in rows],['hi'])
 def test_keywords_support_old_stringified_arrays(self):
  tree=ast.parse((Path(__file__).resolve().parents[1]/'scripts/build.py').read_text())
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='article_keywords')
  import re
  scope={'re':re,'title':lambda p,l:'Title','category':lambda p:'technology','CATEGORIES':{'technology':('Technology','तकनीक')}}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'keywords','exec'),scope)
  terms=scope['article_keywords']({'en_keywords':"['Cricket', 'World Cup']"},'en')
  self.assertEqual(terms[:2],['Cricket','World Cup'])
