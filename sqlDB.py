import pandas as pd
import sqlite3
import gamry_parser as parser

#Converts dta files to csv files
def dtaParser(s):
    gp = parser.GamryParser()
    gp.load(s)
    curve_count = gp.get_curve_count()
    header = gp.get_header()

    #create a csv document for the header
    createHeader(gp.get_header())
    
    #create multiple files depending on how many curves it currently has
    for i in range(curve_count):
        curve_data = gp.get_curve_data(i)
        curve_data.to_csv(f'data{i + 1}.csv', index=False)

#Saving the Header info to the csv document
def createHeader(s):
    df=pd.DataFrame(s)
    df.to_csv('header.csv', index=False)
    

#Using SQL queries to read and alter the csv file to create a new file that contains a table with all the requested information
def reading(dataFile, sqlQuery):
    df=pd.read_csv(dataFile)
    conn = sqlite3.connect(":memory:")
    df.to_sql("my_table", conn, index=False)

    #SQL query to pull the necessary data from the csv  file
    query = sqlQuery

    result_df =  pd.read_sql_query(query, conn)
    result_df.to_csv(f"output_{dataFile}", index = False)

    conn.close()

#It's going to go through the header file and search for its Tag and date
def searchHeader(headerFile):
    df = pd.read_csv(headerFile)
    tag = df.at[0,"TAG"]
    date = df.at[0,"DATE"]
    return {"tag":tag, "date":date}

if __name__ == "__main__":

    #Name of the dta file
    dtaFile = "data.dta"

    query = ""
    dtaParser(dtaFile)

    #Header information - tag, date
    headerInfo = searchHeader("header.csv")
    match headerInfo['tag']:
        case 'CA':
            query = "SELECT T, Vf, Im FROM 'my_table'"
        case 'CV':
            query = "SELECT VF, Im FROM 'my_table'"
    
    reading("data1.csv",query)

