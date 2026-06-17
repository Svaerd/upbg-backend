import uuid


def get_user_sessions(mongo_db, user_id):
    return list(mongo_db.EXAM_SESSIONS.find({"user_id": user_id}))


def insert_exam_bank(mongo_db, bank_doc):
    mongo_db.EXAM_BANKS.insert_one(bank_doc)


def get_all_exam_banks(mongo_db):
    return list(mongo_db.EXAM_BANKS.find())


def delete_exam_bank(mongo_db, bank_id):
    mongo_db.EXAM_BANKS.delete_one({"_id": bank_id})


def insert_exam_template(mongo_db, template_doc):
    mongo_db.EXAM_TEMPLATE.insert_one(template_doc)


def get_all_exam_templates(mongo_db):
    return list(mongo_db.EXAM_TEMPLATE.find())


def delete_exam_template(mongo_db, template_id):
    mongo_db.EXAM_TEMPLATE.delete_one({"_id": template_id})


def get_session_by_registration(mongo_db, registration_id):
    return mongo_db.EXAM_SESSIONS.find_one({"registration_id": registration_id})


def get_template_by_test_type(mongo_db, test_type_name):
    return mongo_db.EXAM_TEMPLATE.find_one({"test_type": test_type_name})


def get_random_questions(mongo_db, test_type_name, section, amount):
    pipeline = [
        {"$match": {"test_type": test_type_name, "section": section}},
        {"$sample": {"size": amount}},
        {"$project": {"_id": 1}},
    ]
    return list(mongo_db.EXAM_BANKS.aggregate(pipeline))


def insert_exam_session(mongo_db, session_doc):
    mongo_db.EXAM_SESSIONS.insert_one(session_doc)


def get_session_by_id_and_user(mongo_db, session_id, user_id):
    return mongo_db.EXAM_SESSIONS.find_one({"_id": session_id, "user_id": user_id})


def upsert_exam_answer(mongo_db, session_id, question_id, answer_doc):
    mongo_db.EXAM_ANSWERS.update_one(
        {"session_id": session_id, "question_id": question_id},
        {
            "$set": answer_doc,
            "$setOnInsert": {"_id": f"ANS_{uuid.uuid4().hex[:10].upper()}"},
        },
        upsert=True,
    )


def get_banks_by_ids(mongo_db, question_ids):
    return list(mongo_db.EXAM_BANKS.find({"_id": {"$in": question_ids}}))


def get_answers_by_session(mongo_db, session_id):
    return list(mongo_db.EXAM_ANSWERS.find({"session_id": session_id}))


def finish_exam_session(mongo_db, session_id):
    mongo_db.EXAM_SESSIONS.update_one(
        {"_id": session_id}, {"$set": {"status": "FINISHED"}}
    )
