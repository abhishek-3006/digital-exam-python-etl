import csv
import glob
import os
import traceback
from itertools import repeat
from multiprocessing import Pool

import pandas as pd
import datetime

from multiprocessing import Manager


base_dir = "C:/Users/ashetty/Desktop/DeX/Diamond/CRL/Candidate_Logs/"
input_dir = "Diamond/raw1/"
output_dir = "C:/Users/ashetty/Desktop/DeX/Diamond/CRL/Transformed/"
exception_column_list = ["error"]
master_column_list = ["filename"]


def process_file(file_path, question_dict, master_dict):
    try:
        client_id = "Diamond"  # file_path.split("/")[-1].split("_")[0].lower()
        rack_name = file_path.split('\\')[-1]
        Value = 1

        for file in glob.glob(file_path + "/*"):  # batch wise logs folder
            # file_name = file.split("/")[-1]
            file_name = file.split("\\")[-1]
            read_files = []
            exception_rows = []
            output_rows = []
            for sub_file in glob.glob(file + "/*"):  # individual candidate logs

                try:
                    unique_questions = {}
                    exam_id = sub_file.split("\\")[-1].split("-")[0]  # SO711311*** (11 alphanumeric)
                    eed_id = sub_file.split("\\")[-1].split("-")[1]  # 218132 (6 digit)
                    dataframe = (
                        pd.read_csv(
                            sub_file,
                            delimiter="|",
                            names=[
                                "Timestamp",
                                "Section Name",
                                "QuestionID",
                                "CurrentQuestionNumber",
                                "OptionSelected",
                                "AlternateOptionSelected",
                                "Bookmark",
                                "SectionalQuestionNumber",
                                "IPAddress",
                                "Action",
                                "SequenceNumber",
                                "Candidate MachineDateTime",
                                "Timer",
                                "MacAddress",

                            ],
                            low_memory=False,
                        )
                            .reset_index(drop=True)
                    )
                    dataframe = dataframe.dropna()
                    input_csv_data = dataframe.values.tolist()
                    for index, item in enumerate(input_csv_data):
                        if item[4] != -1:
                            item[0] = item[0].replace('INFO - "', "")
                            item[13] = item[13].replace('"', "")
                            unique_key = str(item[2])
                            output_row = [client_id, eed_id, exam_id]
                            output_row.extend(item)
                            output_row.append(Value)
                            unique_questions[unique_key] = output_row
                            key_ques = str(output_row[0]) + "_" + str(output_row[2]) + "_" + str(
                                int(output_row[5]))  # diamond_examid_QuestionID
                            key_master = str(output_row[0]) + "_" + str(output_row[2])
                        else:
                            continue
                        if key_ques in question_dict.keys():
                            output_row.append(question_dict[key_ques][5])
                            output_row.append(question_dict[key_ques][7])
                            output_row.append(question_dict[key_ques][-1])
                        if key_master in master_dict.keys():
                            output_row.append(master_dict[key_master][1])
                            output_row.append(master_dict[key_master][2])
                            output_row.append(master_dict[key_master][3])
                            output_row.append(master_dict[key_master][4])
                            output_row.append(master_dict[key_master][5])
                            output_row.append(master_dict[key_master][8])
                            output_row.append(master_dict[key_master][11])
                            output_row.append(master_dict[key_master][12])
                            output_row.append(master_dict[key_master][13])
                            output_row.append(master_dict[key_master][-6])
                            output_row.append(master_dict[key_master][-5])
                    unique_questions = {
                        k: v
                        for k, v in sorted(unique_questions.items(), key=lambda item: item[1])
                    }
                    sub_file_output_rows = [value for item, value in unique_questions.items()]
                    output_rows.extend(sub_file_output_rows)

                except Exception as ex:
                    print(ex)
                    continue
            output_rows.insert(
                0,
                [
                    "clientid",
                    "eed_id",
                    "examid",
                    "Timestamp",
                    "Section Name",
                    "QuestionID",
                    "CurrentQuestionNumber",
                    "OptionSelected",
                    "AlternateOptionSelected",
                    "Bookmark",
                    "SectionalQuestionNumber",
                    "IPAddress",
                    "Action",
                    "SequenceNumber",
                    "Candidate MachineDateTime",
                    "Timer",
                    "MacAddress",
                    "Value",
                    "mdm_name",
                    "crr_exam_batch",
                    "crr_crct_key",
                    "Zone",
                    "State",
                    "City",
                    "Test Center ID",
                    "Venue Name",
                    "Gender",
                    "Exam Date",
                    "Exam Time",
                    "Category",
                    "PWD",
                    "PWD Extra Time"
                ],
            )

            read_files.append([file_path])
            with open(
                    output_dir + client_id + "_fastest_finger/" + rack_name + "/" + file_name + ".csv",
                    "w",
                    newline="",
            ) as f:
                writer = csv.writer(f)
                writer.writerows(output_rows)

            if os.path.isfile(base_dir + input_dir + "Master.csv"):
                with open(base_dir + input_dir + "Master.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(read_files)
            else:
                with open(base_dir + input_dir + "Master.csv", "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(master_column_list)
                    writer.writerows(read_files)
            if os.path.isfile(base_dir + input_dir + "Exception.csv"):
                with open(base_dir + input_dir + "Exception.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(exception_rows)
            else:
                with open(base_dir + input_dir + "Exception.csv", "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(exception_column_list)
                    writer.writerows(exception_rows)
    except Exception as err:
        traceback.print_exc()
        print("error")


def shared_dict():
    client_id = "Diamond"
    question_set = glob.glob("C:/Users/ashetty/Desktop/DeX/Diamond/QuestionPaper/*.csv")
    master_template = "C:/Users/ashetty/Desktop/DeX/Diamond/Diamond Master Running List.xlsx"
    question_dataframe = pd.DataFrame(
        columns=["crr_eed_id", "crr_reg_no", "eed_exm_id", "eed_client_roll_no", "eed_mdm_id", "mdm_name",
                 "crr_exam_date", "crr_exam_batch", "qtp_sec_seqno",
                 "Section", "crr_qst_no", "candidate_seq_no", "marks", "negative_marks", "crr_answer", "crr_crct_id",
                 "crr_crct_key"])

    #  question paper lookup
    for question_template in question_set:
        question_partial = pd.read_csv(
            question_template,
            delimiter=";",
            names=[
                "crr_eed_id", "crr_reg_no", "eed_exm_id", "eed_client_roll_no", "eed_mdm_id", "mdm_name",
                "crr_exam_date",
                "crr_exam_batch", "qtp_sec_seqno",
                "Section", "crr_qst_no", "candidate_seq_no", "marks", "negative_marks", "crr_answer", "crr_crct_id",
                "crr_crct_key"
            ],
            low_memory=False,
        ).reset_index(drop=True)
        question_dataframe = question_dataframe.append(question_partial)
    question_csv_data = question_dataframe.values.tolist()
    question_dict = {}
    question_temp = [question_dict.update({client_id + "_" + str(item[2]) + "_" + str(item[-7]): item}) for item in
                     question_csv_data]
    master_dataframe = pd.read_excel(
        master_template,
        names=["CandidateID", "Zone", "State", "City", "TestCenterID", "VenueName", "CandidateID", "RegistrationNo.",
               "Gender",
               "DOB", "MemberName", "ExamDate", "ExamTime", "Category", "ModuleID", "ModuleName", "PWD", "PWDExtraTime",
               "Dummy 1", "Dummy 2", "Dummy 3", "Dummy 4"],
    ).reset_index(drop=True)
    master_csv_data = master_dataframe.values.tolist()
    master_dict = {}
    master_temp = [master_dict.update({client_id + "_" + str(item[0]): item}) for item in
                   master_csv_data]
    return question_dict, master_dict


def create_output_files(client_id, rack_name):
    if not os.path.exists(output_dir + client_id + "_fastest_finger/" + rack_name):
        os.mkdir(output_dir + client_id + "_fastest_finger/" + rack_name)


if __name__ == '__main__':
    start_time = datetime.datetime.now()
    client_id = "Diamond"
    list_of_files = glob.glob(base_dir + input_dir + "*")
    files = [file for file in list_of_files if "Master" not in file and "Exception" not in file]
    for i in files:
        rack_name = i.split('\\')[-1]
        create_output_files(client_id, rack_name)
    with Manager() as manager:
        shared_question_dict, shared_master_dict = shared_dict()
        final_question_dict = manager.dict()
        final_master_dict = manager.dict()
        # final_question_dict, final_master_dict = manager.Namespace()
        final_question_dict = shared_question_dict
        final_master_dict = shared_master_dict
        # print(final_master_dict)
        with Pool(2) as pool:
            pool.starmap(process_file, zip(files, repeat(final_question_dict), repeat(final_master_dict)))
            pool.close()
            pool.terminate()
            pool.join()
    print("time taken: " + str(datetime.datetime.now() - start_time))


