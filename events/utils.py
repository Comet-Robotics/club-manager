def format_card_data(data):
    parts = data.split("=")
    if len(parts) < 2:
        return None
    student_id = parts[0]
    student_id = student_id.replace(";", "")
    print(student_id)
    return student_id
