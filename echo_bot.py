from datetime import datetime, timedelta
import telebot
from telebot import types
import config
from mysqlAPI import DBConnect, StateType
import time

bot = telebot.TeleBot(config.TOKEN, parse_mode=None)
DBController = DBConnect()
userDict = {}

class User:
	def __init__(self, name):
		self.name = name
		self.surname = None
		self.email = None

@bot.message_handler(commands=['start'])
def send_welcome(message):

	userId = message.from_user.id

	if (DBController.isUserExist(userId)):
		userName = DBController.getUserName(userId)
		text = "Привет, " + userName + "!\nМы уже знакомы, поэтому можешь пользоваться моим функционалом 😊"
		bot.send_message(userId, text)
		printMenu(message)
		return

	text = """\
Привет, мне надо узнать немного о тебе. 
Как тебя зовут?
"""
	msg = bot.send_message(message.chat.id, text)
	bot.register_next_step_handler(msg, process_name_step)

def isStringValid(inputString):
	contains_digit = any(map(str.isdigit, inputString))
	text_len = [len(x) for x in inputString.split()]
	lenQu = max(text_len) / min(text_len)
	return (not contains_digit) and (lenQu == 1)

def process_name_step(message):
	try:
		chatId = message.chat.id
		name = message.text
		if message.content_type != "text" or not isStringValid(name):
			msg = bot.send_message(chatId, "Что-то не так с именем, введи свое имя еще раз и правильно!")
			bot.register_next_step_handler(msg, process_name_step)
			return
		user = User(name.title())
		userDict[chatId] = user
		msg = bot.send_message(chatId, "Привет "+ user.name +", какая у тебя фамилия?")
		bot.register_next_step_handler(msg, process_surname_step)
	except Exception as e:
		bot.send_message(message.chat.id, "Ого, ты смог сломать меня, начинай заново и не надо так больше делать")

def process_surname_step(message):
	try:
		chatId = message.chat.id
		surname = message.text
		if message.content_type != "text" or not isStringValid(surname):
			msg = bot.send_message(chatId, "Что-то не так с фамилией, введи свою фамилию еще раз и правильно!")
			bot.register_next_step_handler(msg, process_surname_step)
			return
		user = userDict[chatId]
		user.surname = surname.title()
		msg = bot.send_message(chatId, "Остался последний вопрос, введи свой корпаративный Email")
		bot.register_next_step_handler(msg, process_email_step)
	except Exception as e:
		bot.send_message(message.chat.id, "Ого, ты смог сломать меня, начинай заново и не надо так больше делать")
	
def process_email_step(message):
	try:
		chatId = message.chat.id
		email = message.text
		if message.content_type != "text":
			msg = bot.send_message(chatId, "Только текст! Давай по новой")
			bot.register_next_step_handler(msg, process_email_step)
			return
		user = userDict[chatId]
		user.email = email
		DBController.addUser(chatId, user.name, user.surname, user.email)
		del userDict[chatId]
		bot.send_message(chatId, "Ты в системе 😎")
		bot.send_message(chatId, "Теперь мой функционал доступен для тебя, я могу хранить время твоего прихода и ухода, время твоего обеда и даже строить месячный отчет!")
		bot.send_message(chatId, "Как только ты придешь или уйдешь с работы - оповести меня об этом! (возможно в будущем я научусь тебе напоминать об этом)")
		printMenu(message)
	except Exception as e:
		print(e)
		bot.send_message(message.chat.id, "Ого, ты смог сломать меня, начинай заново и не надо так больше делать")

def printMenu(message):
	markup = types.ReplyKeyboardMarkup(selective=False, resize_keyboard=True)
	come = types.KeyboardButton('Пришел')
	gone = types.KeyboardButton('Ушел') 
	markup.row(come, gone)
	msg = bot.send_message(message.chat.id, 'Выбери действие', reply_markup=markup)
	bot.register_next_step_handler(msg, process_new_task)

@bot.message_handler(commands=['file'])
def showButton(message):
	doc = open('test.xlsx', 'rb')
	bot.send_document(message.from_user.id, doc)
	markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
	itembtn1 = types.KeyboardButton('/file')
	markup.add(itembtn1)
	bot.reply_to(message, "Choose one letter:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def process_new_task(message):
	if (message.content_type != "text"):
		return
	
	case = message.text

	if (case == "Пришел"):
		process_come_task(message)
	elif (case == "Ушел"):
		process_gone_task(message)


def process_come_task(message):
	userId = message.from_user.id
	if (DBController.getLastTask(userId) != StateType.Gone.id):
		msg = bot.send_message(message.chat.id, '(Ты уже на работе)')
		return
	
	DBController.setUserCome(userId)
	msg = bot.send_message(message.chat.id, 'Удачного тебе дня!')
	bot.register_next_step_handler(msg, process_new_task)

def process_gone_task(message):
	userId = message.from_user.id
	if (DBController.getLastTask(userId) != StateType.Come.id):
		msg = bot.send_message(message.chat.id, '(Ты уже ушел)')
		return
	
	comeTime = DBController.getTimeLastTask(message.from_user.id)
	deltaTime = datetime.now() - comeTime
	if (deltaTime < timedelta(seconds=5)):
		show_mistake_action(message)
		return

	text = message.text

	if not text.isdigit():
		process_dinner_time(message)
		return
		
	recordId = DBController.setUserGone(message.from_user.id)
	DBController.setSpendTimeForDinner(message.from_user.id, recordId, int(text))

	workingTime = datetime.now() - comeTime - timedelta(minutes=int(text))

	bot.send_message(message.chat.id, f'Ты сегодня отработал {workingTime.seconds // 3600} часов {(workingTime.seconds // 60) % 60} минут')
	bot.send_message(message.chat.id, f'Пришел в {comeTime.hour}:{comeTime.minute}')
	bot.send_message(message.chat.id, f'Ушел в {datetime.now().hour}:{datetime.now().minute}')
	msg = bot.send_message(message.chat.id, 'Пока!')
	printMenu(message)

def process_dinner_time(message):
	markup = types.ReplyKeyboardRemove(selective=False)
	msg = bot.send_message(message.chat.id, 'Один вопрос, пока ты не ушел, сколько потратил время на обед (в минутах)', reply_markup=markup)
	bot.register_next_step_handler(msg, process_gone_task)
	return


def show_mistake_action(message):
	markup = types.ReplyKeyboardMarkup(selective=False, resize_keyboard=True,)
	yes = types.KeyboardButton('Да')
	no = types.KeyboardButton('Нет') 
	markup.row(yes, no)
	bot.send_message(message.chat.id, 'Думаю ты нажал случайно')
	msg = bot.send_message(message.chat.id, 'Ты точно ушел домой?', reply_markup=markup)
	bot.register_next_step_handler(msg, process_mistake_action)

def process_mistake_action(message):
	if (message.content_type != "text"):
		return
	
	case = message.text

	if case == "Да":
		bot.send_message(message.chat.id, 'Я удалю твою старую запись о твоем приходе, так как между действиями прошло мало времени')
		DBController.deleteLastTask(message.chat.id)
	elif case == "Нет":
		bot.send_message(message.chat.id, 'Все норм, сделаем вид, что этого не было')
	else:
		bot.send_message(message.chat.id, 'Я только "Да" или "Нет"')
		process_mistake_action(message)
		return
	printMenu(message)

@bot.message_handler(commands=['test'])
def getId(message):
	user = message.from_user.id
	print(user)
	markup = types.ReplyKeyboardMarkup(row_width=2)
	itembtn1 = types.KeyboardButton('/test')
	markup.add(itembtn1)
	bot.reply_to(message, "hueta123", reply_markup=markup)

if __name__ == "__main__":
	while True:
		try:
			bot.polling(none_stop=True, timeout=30)
		except:
			print("Bot restart")
			time.sleep(15)

