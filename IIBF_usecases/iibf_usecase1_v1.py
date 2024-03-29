import csv
import datetime
import glob
import os
import shutil
import traceback
from itertools import repeat
from multiprocessing import Pool
import pandas as pd
# from memory_profiler import profile
import logging

base_dir = "C:\\Users\\ashetty\\Desktop\\FastestFinger\\"
input_dir = "raw\\"
output_dir = "C:\\Users\\ashetty\\Desktop\\FastestFinger\\"

exception_column_list = ["error"]
master_column_list = ["filename"]
log_path = "C:/Users/ashetty/Desktop/DeX/logs/"


def log_setup(name, filename, level):
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        "%(levelname)s: %(asctime)s %(message)s", datefmt="%d/%m/%Y %I:%M:%S %p"
    )
    fileHandler = logging.FileHandler(log_path + filename, mode="a")
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    if level == "info":
        logger.setLevel(logging.INFO)
    elif level == "error":
        logger.setLevel(logging.ERROR)

    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)
    return logger


def log_message(message, level, name):
    if name == "system_log":
        log = logging.getLogger("INFO")
    if name == "error_log":
        log = logging.getLogger("ERROR")
    if level == "error":
        log.error(message)
    if level == "info":
        log.info(message)


log_setup(
    "INFO",
    datetime.datetime.today().strftime("%d%m%Y") + "_process_executed.log",
    "info",
)
log_setup(
    "ERROR", datetime.datetime.today().strftime("%d%m%Y") + "_errors.log", "error"
)


def process_file(file_path, question_dict, master_dict, count_list):
    try:

        exam_start_str = "Clicked on 'OK' of Start Exam Dialog Box|Clicked on 'Start Exam' button"
        client_id = file_path.split("\\")[-3]
        log_message(
            "Current working directory: " + file_path,
            "info",
            "system_log",
        )
        rack_name = file_path.split('\\')[-1]
        Value = 1

        for file in glob.glob(file_path + "\\*"):  # batch wise logs folder
            file_name = file.split("\\")[-1]
            read_files = []
            output_rows = []

            for sub_file in glob.glob(file + "\\5208693-5192-N.log"):  # individual candidate log file

                try:
                    unique_questions = {}
                    membership_no = sub_file.split("\\")[-1].split("-")[0]  # SO711311*** (11 alphanumeric)
                    enrollment_id = sub_file.split("\\")[-1].split("-")[1]  # 218132 (6 digit)
                    dataframe = (
                        pd.read_csv(
                            sub_file,
                            delimiter='|', quoting=3,
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
                                "Timer"
                            ],
                            low_memory=False,
                        )
                            .reset_index(drop=True)
                    )
                    dataframe[['IPAddress']] = dataframe[['IPAddress']].fillna('0')
                    dataframe[['Action']] = dataframe[['Action']].fillna('NA')
                    # ind = dataframe.index[dataframe['Action'].str.contains("Start Exam", case=False)]  # indentifying index for Ok button
                    ind = dataframe.index[dataframe['Action'].str.contains(exam_start_str)]
                    if list(ind):
                        dataframe = dataframe.iloc[ind[0]+1:]  # taking only rows below the OK button row
                    res = [i for i in list(dataframe['IPAddress']) if 'PC change' in i]
                    dataframe.loc[dataframe['IPAddress'].str.contains('PC Change', case=False), 'IPAddress'] = 'PC Change Point'
                    dataframe['Section Name'] = dataframe['Section Name'].fillna('nan')

                    dataframe = dataframe[(dataframe.Action == 'RS') | (dataframe.IPAddress == 'PC Change Point')]
                    dataframe = dataframe.drop_duplicates(subset=['QuestionID', 'Action'], keep='last').reset_index(drop=True)
                    input_csv_data = dataframe.values.tolist()
                    item = []
                    output_row = []
                    x = 1
                    pc_counter = 0
                    flag = 0
                    pc_counter_list = []
                    correct_cnt = 0
                    incorrect_cnt = 0
                    attempt_cnt = 0
                    correct_store = ''
                    attempt_store = ''
                    incorrect_store = ''
                    for index, item in enumerate(input_csv_data):
                        if item[4] != -1 and (item[9] == 'RS' or item[8] == 'PC Change Point'):
                            item[0] = item[0].replace('INFO - "', "")
                            item[12] = str(item[12]).replace('"', '')
                            if item[12] == '00:00':
                                item[12] = '00:00:00'
                            unique_key = str(item[2])
                            output_row = [client_id, enrollment_id, membership_no, len(res)]
                            output_row.extend(item)
                            output_row.append(Value)
                            output_row.append('Appeared-Attempted')
                            if 'PC Change' in input_csv_data[index - 1][8] and index != 0:  # pc counter column
                                pc_counter += 1
                                output_row.append(pc_counter)
                            else:
                                output_row.append(pc_counter)
                            if unique_questions:
                                prev_pc_counter = list(unique_questions.items())[-1][1][19]
                            else:
                                prev_pc_counter = 0
                            if str(output_row[6]) != 'nan':
                                unique_questions[unique_key] = output_row
                                key_ques = str(output_row[0]) + "_" + str(output_row[1]) + "_" + str(
                                int(output_row[6]))  # diamond_eedid_QuestionID
                                key_master = str(output_row[0]) + "_" + str(output_row[2]) + "_" + str(output_row[1])
                            else:
                                if str(input_csv_data[index][2]) == 'nan' and str(
                                        input_csv_data[index - 1][2]) == 'nan':  # two quick pc changes
                                    if index == 0 or index - 1 == 0:  # at the very start
                                        correct_store = '0|'
                                        incorrect_store = '0|'
                                        attempt_store = '0|'
                                    else:
                                        if flag == 0:  # at the in between stage
                                            correct_store = str(correct_cnt) + '|0|'
                                            incorrect_store = str(incorrect_cnt) + '|0|'
                                            attempt_store = str(attempt_cnt) + '|0|'
                                            correct_cnt = 0
                                            incorrect_cnt = 0
                                            attempt_cnt = 0
                                            flag = 1
                                        elif flag == 1:  # trying to handle more than 2 quick pc changes
                                            correct_store = correct_store + '0|'
                                            incorrect_store = incorrect_store + '0|'
                                            attempt_store = attempt_store + '0|'
                                if input_csv_data[index] == input_csv_data[-1]:  # at the very end
                                    correct_store = correct_store + str(correct_cnt)
                                    incorrect_store = incorrect_store + str(incorrect_cnt)
                                    attempt_store = attempt_store + str(attempt_cnt)
                                key_ques = ''
                                key_master = ''
                                unique_questions['PC_change_'+str(x)] = output_row
                                x += 1
                        else:
                            continue
                        if key_ques in question_dict.keys():
                            output_row.append(question_dict[key_ques][3])  # Medium Code
                            output_row.append("08:30-10:30")  # batch time
                            output_row.append(question_dict[key_ques][-1])  # Correct Answer
                            if item[4] == output_row[22]:
                                output_row.append('Correct')
                            else:
                                output_row.append('Incorrect')
                            # store logic snippet start
                            if pc_counter == prev_pc_counter+1 and flag != 1:  # general pc change occurs
                                correct_store = correct_store + str(correct_cnt)+'|'
                                incorrect_store = incorrect_store + str(incorrect_cnt) + '|'
                                attempt_store = attempt_store + str(attempt_cnt) + '|'
                                correct_cnt = 0
                                incorrect_cnt = 0
                                attempt_cnt = 0
                                if output_row[23] == 'Correct':
                                    attempt_cnt += 1
                                    correct_cnt += 1
                                elif output_row[23] == 'Incorrect':
                                    attempt_cnt += 1
                                    incorrect_cnt += 1
                            elif pc_counter == prev_pc_counter:
                                if output_row[23] == 'Correct':
                                    attempt_cnt += 1
                                    correct_cnt += 1
                                elif output_row[23] == 'Incorrect':
                                    attempt_cnt += 1
                                    incorrect_cnt += 1
                                if input_csv_data[index] == input_csv_data[-1]:
                                    correct_store = correct_store + str(correct_cnt)
                                    incorrect_store = incorrect_store + str(incorrect_cnt)
                                    attempt_store = attempt_store + str(attempt_cnt)

                        else:
                            output_row.extend(("NA", "NA", "NA", "NA"))
                        if key_master in master_dict.keys():
                            output_row.append(master_dict[key_master][0])  # zone
                            output_row.append(master_dict[key_master][1])  # city
                            output_row.append(master_dict[key_master][2])  # test center id/ venue id
                            output_row.append(master_dict[key_master][3])  # venue name
                            output_row.append(master_dict[key_master][6])  # exam date
                            output_row.append(master_dict[key_master][7])  # exam time
                            output_row.append(master_dict[key_master][8])  # pwd
                            output_row.append(master_dict[key_master][9])  # module id
                            output_row.append(master_dict[key_master][10])  # module name
                            output_row.append(master_dict[key_master][11])  # exams
                        else:
                            output_row.extend(("NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA"))
                    if not output_row and item:  # for not attempted single row addition
                        if item[4] == -1:
                            item[0] = item[0].replace('INFO - "', "")
                            item[12] = item[12].replace('"', '')
                            output_row = [client_id, enrollment_id, membership_no, len(res)]
                            item[12] = '23:00:00'
                            output_row.extend(item)
                            output_row.append(Value)
                            output_row.append('Appeared-Not-Attempted')
                            output_row.append(0)
                            unique_key = str(item[2])
                            unique_questions[unique_key] = output_row
                            key_ques = str(output_row[0]) + "_" + str(output_row[1]) + "_" + str(
                                int(output_row[6]))  # diamond_examid_QuestionID
                            key_master = str(output_row[0]) + "_" + str(output_row[2]) + "_" + str(output_row[1])
                            if key_ques in question_dict.keys():
                                output_row.append(question_dict[key_ques][3])
                                output_row.append("08:30-10:30")
                                output_row.append(question_dict[key_ques][-1])
                            else:
                                output_row.extend(("NA", "NA", "NA"))
                            if key_master in master_dict.keys():
                                output_row.append(master_dict[key_master][0])  # zone
                                output_row.append(master_dict[key_master][1])  # city
                                output_row.append(master_dict[key_master][2])  # test center id/ venue id
                                output_row.append(master_dict[key_master][3])  # venue name
                                output_row.append(master_dict[key_master][6])  # exam date
                                output_row.append(master_dict[key_master][7])  # exam time
                                output_row.append(master_dict[key_master][8])  # pwd
                                output_row.append(master_dict[key_master][9])  # module id
                                output_row.append(master_dict[key_master][10])  # module name
                                output_row.append(master_dict[key_master][11])  # exams
                            else:
                                output_row.extend(("NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA"))
                    item.clear()
                    # unique_questions = {
                    #     k: v
                    #     for k, v in sorted(unique_questions.items(), key=lambda item: item[1])
                    # }
                    sub_file_output_rows = [value for item, value in unique_questions.items()]
                    if sub_file_output_rows:
                        for ele in sub_file_output_rows:
                            pc_counter_list.append(ele[19])
                        max_cnt = sorted(pc_counter_list)[-1]
                    for element in sub_file_output_rows:
                        element.extend((correct_store, incorrect_store, attempt_store))
                        if element[19] == 0:
                            element.append('No PC change')
                        elif element[19] == 1:
                            element.append('First PC change')
                        elif element[19] == max_cnt:
                            element.append('Last PC change')
                    output_rows.extend(sub_file_output_rows)
                    if sub_file_output_rows:
                        count_list.append(1)

                except Exception as ex:
                    traceback.print_exc()
                    print(sub_file)
                    continue
            output_rows.insert(
                0,
                [
                    "clientid",
                    "eed_id",
                    "examid",
                    "PC_change_request",
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
                    "Value",
                    "appearance status",
                    "pc_counter",
                    "medium code",
                    "crr_exam_batch",
                    "crr_crct_key",
                    # "Candidate Identification",
                    "Status",
                    "Zone",
                    "City",
                    "Test Center ID",
                    "Venue Name",
                    "Exam Date",
                    "Exam Time",
                    "PWD",
                    "Module ID",
                    "Module name",
                    "Exams",
                    "correct_store",
                    "incorrect_store",
                    "attempted_store",
                    "pc_change_status",
                ],
            )

            read_files.append([file])

            with open(
                    output_dir + client_id + "\\transformed\\" + rack_name + "\\" + file_name + ".csv",
                    "w",
                    newline="",
            ) as f:
                writer = csv.writer(f)
                writer.writerows(output_rows)

            with open(output_dir + client_id + '\\' + "Master.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(read_files)
        log_message(
            "Processing ended: " + file_path,
            "info",
            "system_log",
        )
        return count_list
    except Exception as err:
        traceback.print_exc()
        with open(output_dir + client_id + '\\' + "Exception.csv", "a", newline="") as f:
            f.write(str(err))


def create_output_files(client_name_value, rack_name_value):
    if not os.path.exists(output_dir + client_name_value + "\\transformed\\" + rack_name_value):
        os.mkdir(output_dir + client_name_value + "\\transformed\\" + rack_name_value)
    if not os.path.exists(base_dir + client_name_value + "\\Master.csv"):
        with open(base_dir + client_name_value + "\\Master.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(master_column_list)
    if not os.path.exists(base_dir + client_name_value + "\\Exception.csv"):
        with open(base_dir + client_name_value + "\\Exception.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(exception_column_list)


def main(list_of_folders):
    start_time = datetime.datetime.now()
    for folder in list_of_folders:
        list_of_files = glob.glob(folder + '\\' + input_dir + "*")
        client_name = folder.split("\\")[-1]
        files = [file for file in list_of_files if "Master" not in file and "Exception" not in file]
        for i in list_of_files:
            diamond_rack_name = i.split('\\')[-1]
            create_output_files(client_name, diamond_rack_name)
        question_set = glob.glob(base_dir + client_name + '\\' + 'CRR\\*.csv')
        master_set = glob.glob(base_dir + client_name + '\\Master\\*.xlsx')
        question_dataframe = pd.DataFrame(
            columns=["Exam Code", "Membership No.", "Enrollment Id of NSE IT", "Medium Code", "Question Paper Id", "Question Id", "Candidate Response", "Correct Answer"])
        master_dataframe = pd.DataFrame(
            columns=["Region/ Zone", "City", "Venue ID", "Venue Name", "Candidate Id", "Enroll. No.", "Exam Date", "Exam Time", "PWD", "Module ID", "Module Name", "EXAMS"])

        #  question paper lookup
        for question_template in question_set:
            question_partial = pd.read_csv(
                question_template,
                delimiter=",",
                usecols=[
                    "Exam Code","Membership No.", "Enrollment Id of NSE IT", "Medium Code","Question Paper Id","Question Id","Candidate Response","Correct Answer"
                ],
                low_memory=False,
            ).reset_index(drop=True)
            question_dataframe = question_dataframe.append(question_partial)
            question_dataframe = question_dataframe.fillna('NA')
        question_csv_data = question_dataframe.values.tolist()
        final_question_dict = {}
        question_temp = [final_question_dict.update({client_name + "_" + str(item[2]) + "_" + str(item[-3]): item}) for
                         item in question_csv_data]  # diamond_eedid_qstno

        #  master data lookup
        for master_template in master_set:
            master_partial = pd.read_excel(
                master_template,
                usecols=["Region/ Zone", "City", "Venue ID", "Venue Name", "Candidate Id", "Enroll. No.", "Exam Date", "Exam Time", "PWD", "Module ID", "Module Name", "EXAMS" ]
            ).reset_index(drop=True)
            master_dataframe = master_dataframe.append(master_partial)
            master_dataframe = master_dataframe.fillna('NA')
            master_csv_data = master_dataframe.values.tolist()
            final_master_dict = {}
            master_temp = [final_master_dict.update({client_name + "_" + str(item[4]) + "_" + str(item[5]): item}) for item in
                           master_csv_data]

        del question_dataframe, master_dataframe, question_partial, question_csv_data, master_csv_data, question_temp, master_temp
        count_list = []
        final_count_list = []
        # with Pool(2) as pool:
        #     p = pool.starmap(process_file, zip(files, repeat(final_question_dict), repeat(final_master_dict), repeat(count_list)))
        #     final_count_list.extend(p)
        #     pool.close()
        #     pool.terminate()
        #     pool.join()
        # flat_list = [item for sublist in final_count_list for item in sublist]
        # print(flat_list.count(1))
        for x in files:
            p = process_file(x, final_question_dict, final_master_dict, count_list)
            # print(p)
    log_message(
        "Fastest Finger processing. Time taken: " + str(datetime.datetime.now() - start_time),
        "info",
        "system_log", )


def move_to_archive(list_of_folders):
    for folder in list_of_folders:
        for src in glob.glob(folder + '\\raw\\*'):
            dest = folder + '\\archived\\'
            shutil.move(src, dest)
        for src in glob.glob(folder + '\\CRR\\*'):
            dest = folder + '\\archived\\CRR\\'
            shutil.move(src, dest)
        for src in glob.glob(folder + '\\Master\\*'):
            dest = folder + '\\archived\\Master\\'
            shutil.move(src, dest)


folders = glob.glob(base_dir + '\\*')
main(folders)
strt_time = datetime.datetime.now()
log_message(
    "Moving to Archived Directory ", "info", "system_log", )
# move_to_archive(folders)
log_message(
        "File moved successfully. Time taken: " + str(datetime.datetime.now() - strt_time),
        "info",
        "system_log", )


