from datetime import datetime
from logging import error
import enum
from getpass import getpass
from mysql.connector import connect, Error

class StateType(enum.Enum):
    Come = (0, "Пришел")
    Gone = (1, "Ушел")
    def __init__(self, id, title):
        self.id = id
        self.title = title

class DBConnect:

    def __init__(self) -> None:
        try:
            self.connection = connect(
                host="localhost",
                user="TelegramBot",
                password="qweASD123",
                database="telegramBotTable"
            )
        except Error as e:
            print (e)
            self.isInit = False
        self.isInit = True

    def closeConnection(self):
        self.connection.close()

    def addUser(self, telegramId:int, name:str, surname:str, email:str):
        cursor = self.connection.cursor()
        query = ("INSERT INTO userData(telegramId, name, surname, email) VALUES(%s, %s, %s, %s)")
        userData = (telegramId, name, surname, email)
        cursor.execute(query, userData)
        self.connection.commit()
        cursor.close()

    def isUserExist(self, telegramId:int)->bool:
        cursor = self.connection.cursor()
        query = "SELECT COUNT(*) FROM userData WHERE telegramId = " + str(telegramId)
        userData = (telegramId)
        cursor.execute(query, userData)
        countResult = cursor.fetchone()[0]
        cursor.close()
        return countResult
    
    def getUserName(self, telegramId:int)->str:
        cursor = self.connection.cursor()
        query = "SELECT name FROM userData WHERE telegramId = " + str(telegramId)
        userData = (telegramId)
        cursor.execute(query, userData)
        result = cursor.fetchone()[0]
        cursor.close()
        return result

    def setUserCome(self, telegramId:int):
        cursor = self.connection.cursor()
        query = ("INSERT INTO timeTable(telegramId, type) VALUES(%s, %s)")
        userData = (telegramId, StateType.Come.id)
        cursor.execute(query, userData)
        self.connection.commit()
        cursor.close()

    def setUserGone(self, telegramId:int)->int:
        cursor = self.connection.cursor()
        query = ("INSERT INTO timeTable(telegramId, type) VALUES(%s, %s)")
        userData = (telegramId, StateType.Gone.id)
        cursor.execute(query, userData)
        self.connection.commit()
        lastRowId = cursor.lastrowid
        cursor.close()
        return lastRowId
    
    def setSpendTimeForDinner(self, telegramId:int, goneTimeId:int, spendTime:int):
        cursor = self.connection.cursor()
        query = ("INSERT INTO dinnerTime(telegramId, timeTableId, dinnerTime) VALUES(%s, %s, %s)")
        userData = (telegramId, goneTimeId, spendTime)
        cursor.execute(query, userData)
        self.connection.commit()
        cursor.close()

    def getLastTask(self, telegramId:int)->int:
        cursor = self.connection.cursor()
        query = "SELECT type FROM timeTable WHERE telegramId = %s ORDER BY id DESC LIMIT 1" 
        cursor.execute(query, (telegramId,))
        result = cursor.fetchone()
        cursor.close()
        if result is None:
            return StateType.Gone.id
        return result[0]

    def getTimeLastTask(self, telegramId:int)->datetime:
        cursor = self.connection.cursor()
        query = "SELECT date FROM timeTable WHERE telegramId = %s ORDER BY id DESC LIMIT 1"
        cursor.execute(query, (telegramId,))
        result = cursor.fetchone()
        cursor.close()
        if result is None:
            return datetime.now() - datetime.timedelta(days=1)
        return result[0]

    def deleteLastTask(self, telegramId:int)->None:
        cursor = self.connection.cursor()
        query = "DELETE FROM timeTable WHERE id = (SELECT * FROM (SELECT id FROM timeTable WHERE telegramId = %s ORDER BY id DESC LIMIT 1) AS t1)"
        cursor.execute(query, (telegramId,))
        self.connection.commit()
        cursor.close()

    def getHoursAndTypeInSpecifiedMonth(self, telegramId:int, numberOfMonth:int):
        cursor = self.connection.cursor()
        query = "SELECT id, date, type FROM timeTable WHERE telegramId = %s AND month(date) = %s"
        cursor.execute(query, (telegramId,numberOfMonth,))
        result = cursor.fetchall()
        cursor.close()
        return result

    def getDinnerTime(self, timeTableId:int)->int:
        cursor = self.connection.cursor()
        query = "SELECT dinnerTime FROM dinnerTime WHERE timeTableId = %s"
        cursor.execute(query, (timeTableId,))
        result = cursor.fetchone()
        cursor.close()
        if result == None:
            return 0
        return result[0]