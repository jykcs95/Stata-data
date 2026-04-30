import pandas as pd
import sqlite3
import gamry_parser as parser

#Using SQL queries to read and pull from the csv file
def reading():
    df=pd.read_csv("data.csv")
    query = "SELECT * FROM df LIMIT 5"

#Converts dta files to csv files
def dtaParser(s):
    gp = parser.GamryParser()
    gp.load(s)
    curve_count = gp.get_curve_count()
    #create multiple files depending on how many curves it currently has
    for i in range(curve_count):
        curve_data = gp.get_curve_data(i)
        curve_data.to_csv(f'data{i + 1}.csv', index=False)


if __name__ == "__main__":
    fileName = "data.dta"
    dtaParser(fileName)