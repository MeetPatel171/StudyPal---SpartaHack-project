import difflib
from pulp import *
import numpy as np 
import pandas as pd
np.random.seed(0)




#Define the variables
names = ['Ben','Kate','Thinh','Jorge','Alfredo','Francisco','Olivia','Omar','sam','ella']

c = np.random.randint(0,len(names), (len(names),len(names)))
np.fill_diagonal(c,0)
print(c)
prob = LpProblem("Matching_Employees", LpMaximize)


employees = range(len(names))
y = LpVariable.dicts("pair", [(i,j) for i in employees for j in employees] ,cat='Binary')

numPerTeam = 2
group = len(names)/numPerTeam
match_info = pd.DataFrame(c, index=names, columns=names)

prob += lpSum([(c[i][j] + c[j][i]) * y[(i,j)] for i in employees for j in employees])

for i in employees:
    prob += lpSum(y[(i,j)] for j in employees) <= numPerTeam-1
    prob += lpSum(y[(j,i)] for j in employees) <= numPerTeam-1
    prob += lpSum(y[(i,j)] for j in employees)+ lpSum(y[(j,i)] for j in employees) <= 1


prob += lpSum(y[(i,j)] for i in employees for j in employees) == group

prob.solve()

print("Finish matching!\n")
for i in employees:
    for j in employees:
        if y[(i,j)].varValue == 1:
            print('{} and {} with preference score {} and {}. Total score: {}'.format(names[i],names[j],c[i,j], c[j,i], c[i,j] +c[j,i]))
            
pulp.value(prob.objective)

s1=[1,8,3,9,4,9,3,8,1,2,3]
s2=[1,8,1,3,9,4,9,3,8,1,2,3]
sm=difflib.SequenceMatcher(None,s1,s2)
print(round(sm.ratio()*10,1)) # similarity with other person (a list)
