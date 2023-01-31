import copy
import heapq
from functools import total_ordering
import string
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import firestore
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import difflib
#import numpy as np
#import pandas as pd
import json, time
import os
from twilio.rest import Client
from flask import *


# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
'''




'''


# Initialize Firebase
cred = credentials.Certificate("./teammatcher-4a022-4f44450bbcca.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://teammatcher-4a022.firebaseio.com/'
})
# Connect to Firestore
db = firestore.client()
# Get the list of students from Firestore

# Use the application default credentials
cred = credentials.ApplicationDefault()

ex_stud = [
    {"type": "student", "name": "Sam", "classes": ["CSE232", "ISS320", "IBIO219"], "Q_ANS": [0, 2, 10, 2, 3]},
    {"type": "student", "name": "Sam", "classes": ["CSE232", "ISS320", "IBIO219"], "Q_ANS": [10, 2, 7, 2, 4]},
    {"type": "student", "name": "Sam", "classes": ["CSE232", "ISS320", "IBIO219"], "Q_ANS": [9, 2, 0, 2, 6]},
    {"type": "student", "name": "Sam", "classes": ["CSE232", "ISS320", "IBIO219"], "Q_ANS": [4, 2, 1, 2, 1]},
    {"type": "student", "name": "Sam", "classes": ["CSE232", "ISS320", "IBIO219"], "Q_ANS": [7, 2, 6, 2, 5]},
    {"type": "student", "name": "Sam", "classes": ["CSE232", "ISS320", "IBIO219"], "Q_ANS": [3, 2, 5, 2, 2]},
    {"type": "student", "name": "Sam", "classes": ["CSE232", "ISS320", "IBIO219"], "Q_ANS": [7, 2, 7, 2, 4]},

]

# The minimum score required to partner two people up
SCORE_THRESHOLD = 3

# The maximum group size
GROUP_SIZE = 4

@total_ordering
class StudentWrapper:
    def __init__(self, student_id, val, score):
        self.id = student_id
        self.val = val
        self.score = score

    def __lt__(self, other):
        return self.score > other.score

    def __eq__(self, other):
        return self.score == other.score


def calculate_score(student_answers, answers):
    """
    Calculates a score for a student based on how similar their answers are to other students' answers.
    """
    sm = difflib.SequenceMatcher(None, student_answers, answers)
    return round(sm.ratio() * 10, 1)  # similarity with other person (a list)

def find_match_single(student, matched, unmatched):
    student_id = student["email"]

    for cl in student["classes"]:
        placed = False

        # Attempt to match our student into an existing group, only needs to match with one person in group
        if cl in matched:
            groups = matched[cl]

            # For all existing groups in a class, place the student in a group if they match with one person
            for i, existing_group in groups:
                if placed:
                    break
                if len(existing_group) >= GROUP_SIZE:
                    continue

                for other_student in existing_group.values():
                    if calculate_score(student["Q_ANS"], other_student["Q_ANS"]) >= SCORE_THRESHOLD:
                        existing_group[student_id] = student
                        groups[i] = existing_group
                        matched[cl] = groups
                        placed = True
                        break

        if placed:
            continue

        # Groups as a dictionary
        group = dict()
        group[student_id] = student

        if cl in unmatched:
            students = unmatched[cl]
            # Using a max heap to rate students the highest
            rated_students = []
            heapq.heapify(rated_students)

            # Iterate over other students, score the similarity, store in heap
            for other_id, other_student in students.items():
                heapq.heappush(rated_students, StudentWrapper(other_id, other_student,
                                                              calculate_score(student["Q_ANS"],
                                                                              other_student["Q_ANS"])))

            # Pop and add enough students until heap is empty or group full
            for i in range(GROUP_SIZE - 1):
                if len(rated_students) == 0:
                    break

                top = heapq.heappop(rated_students)
                if top.score < SCORE_THRESHOLD:
                    break

                group[top.id] = top.val

        # Group size is too small, ignore
        if len(group) <= 1:
            if cl not in unmatched:
                unmatched[cl] = group
            else:
                for key, val in group:
                    unmatched[cl][key] = val
            continue

        # Add valid group to results
        if cl not in matched:
            matched[cl] = [group]
        else:
            matched[cl].append(group)

    return matched, unmatched


def find_match_all_students(students):
    """
    Finds a group of students with similar answers in the same course for all students.
    :param students: dictionary of students with id as a key
    :param group_size: optional maximum size, default 4
    :returns: matched students in groups per class, and unmatched students per class
    """

    # Split students into large groups per class
    student_classes = dict()
    for student_id, student in students.items():
        for cl in student["classes"]:
            if cl not in student_classes:
                student_classes[cl] = {student_id: student}
            else:
                student_classes[cl][student_id] = student

    result = {}
    unmatched_per_class = {}
    for cl, classmates in student_classes.items():
        # IDs of unmatched students, IDs will be removed ones added to a group
        unmatched_set = set(classmates.keys())

        # Pick a student to form a group around
        for student_id, student in classmates.items():
            # Skip if unmatched
            if student_id not in unmatched_set:
                continue
            unmatched_set.remove(student_id)

            # Groups as a dictionary
            group = dict()
            group[student_id] = student

            # Using a max heap to rate students the highest
            rated_students = []
            heapq.heapify(rated_students)

            # Iterate over other students, score the similarity, store in heap
            for other_id, other_student in classmates.items():
                # Ensure we haven't matched this student
                if other_id not in unmatched_set:
                    continue

                heapq.heappush(rated_students, StudentWrapper(other_id, other_student,
                                                              calculate_score(student["Q_ANS"],
                                                                              other_student["Q_ANS"])))

            # Pop and add enough students until heap is empty or group full
            for i in range(GROUP_SIZE - 1):
                if len(rated_students) == 0:
                    break

                top = heapq.heappop(rated_students)
                if top.score < SCORE_THRESHOLD:
                    break

                unmatched_set.remove(top.id)
                group[top.id] = top.val

            # Group size is too small, ignore
            if len(group) <= 1:
                if cl not in unmatched_per_class:
                    unmatched_per_class[cl] = group
                else:
                    for key, val in group:
                        unmatched_per_class[cl][key] = val
                continue

            # Add valid group to results
            if cl not in result:
                result[cl] = [group]
            else:
                result[cl].append(group)

    return result, unmatched_per_class


def main():
    def add_questions():
        questions_ref = db.collection("questions")
        questions = [
            {"type": "multiple_choice", "question": "What is your favorite color?",
             "options": ["Red", "Blue", "Green", "Yellow", "Purple"], "importance": 6},
            {"type": "boolean", "question": "What is your favorite color?", "options": ["Yes", "No"], "importance": 10},
            {"type": "range", "question": "What is your favorite color?", "min": 0, "max": 10},
            {"type": "search_fr", "question": "What classes are you in?", "options": ["CSE232", "ISS320", "IBIO219"],
             "importance": 10},

        ]
        for i in questions:
            questions_ref.add(i)

    # add_questions()

    students_ref = db.collection("students")
    students_docs = students_ref.get()
    if not students_docs:
        print("No students found")
        for i in ex_stud:
            students_ref.add(i)

    students = dict()
    for doc in students_docs:
        stuDict = doc.to_dict()
        students[stuDict["email"]] = stuDict
        print(students[stuDict["email"]])
    print(students)
    # Get the answers to the questions from the iOS app

    # Find the best match for the student based on their answers
    best_match, unmatched = find_match_all_students(students)

    # Save the match to Firestore
    match_ref = db.collection("matches")

    for key, val in best_match.items():
        print("Study groups for class", key, ":")
        for j, group in enumerate(val):
            data = {str(j): list(group.keys())}
            if not match_ref.document(key).get().exists:
                match_ref.add(data, key)
            else:
                match_ref.document(key).update(data)
            for _, student in group.items():
                print(student["name"], end=" ")
            print()
        print(key, val)

    unmatched_ref = db.collection("unmatched")

    print(unmatched)
    for key, val in unmatched.items():
        print("Unmatched students for class", key, ":")
        data = {"students": list(val.keys())}
        if not unmatched_ref.document(key).get().exists:
            unmatched_ref.add(data, key)
        else:
            unmatched_ref.document(key).update(data)

classes = []
main()


client = Client('AC7b2b7670855f07d23b392c5053631cbc', 'f9dd685a6b28893f6777c5ee9f7319e4')

def send_notif(person,type):
    if type == "match":
        client.messages \
                .create(
                     body="Congratulations "+string.capwords(person["name"])+"! We have found a match for you! More details will be sent your way in a new minutes. - StudyPal",
                    from_='+18333172768',
                    to=person["phone"]
                )
    if type == "confirm":
        
        
        client.messages \
                .create(
                     body="Hello "+string.capwords(person["name"])+", we have recieved your team application request! We will notify you once we have found a match. - StudyPal",
                     from_='+18333172768',
                     to=person["phone"]
                 )

app = Flask(__name__)
@app.route("/",methods=["GET","POST"])
def homePage():
   # return "Hello World"
    return send_file("index.html")

@app.route("/questions.json",methods=["GET","POST"])
def questions():
    return send_file("questions.json")


@app.route("/classes",methods=["GET","POST"])
def classDS():
    return send_file("csvjson.json")
@app.route("/newstudent",methods=["GET","POST"])
def api():
    print(request.json)
    dictionary= {"message": "Your form has been successfuly recieved. You will send you a text message shortly, confirming your application.", "status": 200}
    students_ref = db.collection("students")
    students_docs = students_ref.get()
    students_ref.add(request.json[0])
    send_notif(request.json[0],"confirm")
   
                
                
    json_dump = json.dumps(dictionary)
    return json_dump

if __name__ == "__main__":
    pass
app.run(host="0.0.0.0",port=5000,debug=False)