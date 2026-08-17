from src.reasoning import engine

graph = {
  'nodes': [
    {'id':'college::RV College of Engineering','type':'College','name':'RV College of Engineering'},
    {'id':'comment::c1','type':'Comment','body':'The professors are great and the teaching is very practical with industry projects. Highly recommend.','credibility':1.2,'permalink':'https://reddit.com/r/rvce/comment1'},
    {'id':'comment::c2','type':'Comment','body':'Teaching can be hit or miss; some faculty are outdated and lectures are boring.','credibility':0.8,'permalink':'https://reddit.com/r/rvce/comment2'},
  ],
  'edges': [
    {'u':'comment::c1','v':'college::RV College of Engineering','type':'discusses'},
    {'u':'comment::c2','v':'college::RV College of Engineering','type':'discusses'},
  ]
}
result = {
  'colleges_considered':['RV College of Engineering'],
  'sentiment_summary':{
    'teaching':{'score':0.16,'sample_size':2,'variance':0.4,'confidence_label':'moderate confidence','sources':['comment::c1','comment::c2']}
  },
  'confidence_note':'Based on weighted sentiment and credibility scores.'
}
print('--- BEFORE ---')
print(engine.render_simple(result))
print('\n--- AFTER ---')
print(engine.render_with_excerpts(result, graph))
