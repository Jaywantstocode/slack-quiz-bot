from flask import abort, Flask, jsonify, make_response, request, Response
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import json, logging, os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App

logging.basicConfig(level=logging.DEBUG)

slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)

SCOPES = [
	'https://www.googleapis.com/auth/spreadsheets',
	'https://www.googleapis.com/auth/drive'
]
RECORD_QUESTIONS = "Spreadsheet-id1"
RECORD_ANSWER = "Spreadsheet-id2"

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

app_react = App(token=slack_token)


def getGoogleService():
	scope = ['https://www.googleapis.com/auth/spreadsheets',
	         'https://www.googleapis.com/auth/drive.file',
	         "https://www.googleapis.com/auth/drive"]
	keyFile = 'del-varietas.json'
	credentials = ServiceAccountCredentials.from_json_keyfile_name(keyFile,
	                                                               scopes=scope)
	return build("sheets", "v4", credentials=credentials)


def is_request_valid(req):
	is_token_valid = req.form['token'] == os.environ[
		'SLACK_VERIFICATION_TOKEN']
	is_team_id_valid = req.form['team_id'] == os.environ['SLACK_TEAM_ID']

	return is_token_valid and is_team_id_valid


def get_list(sheet_id: str, range: str):
	service = getGoogleService()
	return service.spreadsheets().values().batchGet(
		spreadsheetId=sheet_id, ranges=range).execute()


@app.route('/quiz', methods=['POST'])
def quiz():
	if not is_request_valid(request):
		abort(400)
	data = get_list(RECORD_QUESTIONS, "A:M")
	for i, item in enumerate(data["valueRanges"][0]["values"]):
		if i == 0:
			continue
		elif item[1] != "1":
			text = item[2]
			choices = item[3]
			choice_list = []
			print(choices)
			for j in range(int(choices)):
				choices = {
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": item[4 + j],
					},
					"value": str(i) + "_" + str(j + 1)
				}
				choice_list.append(choices)
			return jsonify({
				"response_type": 'in_channel',
				"blocks": [
					{
						"type": "section",
						"text": {
							"type": "mrkdwn",
							"text": "　:fire:DON’T MISS OUT :fire: Hello! I brought need-to-know information for you today!"
						}
					},
					{
						"type": "divider"
					},
					{
						"type": "section",
						"text": {
							"type": "mrkdwn",
							"text": "*今日のクイズはこちら！*\n　" + text
						},
						"accessory": {
							"type": "image",
							"image_url": "url",
							"alt_text": "alt text for image"
						}
					},
					{
						"type": "divider"
					},
					{
						"type": "actions",
						"elements": choice_list
					}
				]
			})
	return -1


@app.route("/reaction", methods=["POST"])
def reaction():
	# Parse the request payload
	form_json = json.loads(request.form["payload"])
	# response = client.chat_postMessage(
	# 	channel=form_json["channel"]["id"],
	# 	text=str(form_json)
	# )
	if form_json["type"] != 'block_actions':
		return
	val = form_json["actions"][0]["value"]
	channel_id = form_json["channel"]["id"]
	user = form_json["user"]["id"]
	row = str(int(val.split('_')[0]) + 1)
	user_answer = val.split('_')[1]
	data = \
		get_list(RECORD_ANSWER, "A" + row + ":L" + row)["valueRanges"][0][
			"values"][
			0]
	correct_answer = data[1]
	wrong_answer = data[2]
	correct_choice = data[3]
	list_user = ""
	try:
		list_user = data[int(user_answer) + 3]
	except IndexError as e:
		print(e)
	if has_answered(user, data[4:]):
		try:
			response = client.chat_postEphemeral(
				channel=channel_id,
				text="既に回答しています! 次のクイズまで待とうね！\n",
				user=user
			)
		except SlackApiError as e:
			# You will get a SlackApiError if "ok" is False
			assert e.response["error"]
	else:
		answer(user, channel_id, val, correct_choice, correct_answer, wrong_answer)
		record_answer(user, row, user_answer, list_user)
	return


def has_answered(user: str, data):
	# print(data)
	for string in data:
		if user in string:
			return True
		else:
			return False
	return False


def answer(user, channel_id, val: str, correct_val: str, correct_answer: str, wrong_answer: str):
	if val == correct_val:
		try:
			response = client.chat_postEphemeral(
				channel=channel_id,
				text="正解! \n" + correct_answer,
				user=user
			)

		except SlackApiError as e:
			# You will get a SlackApiError if "ok" is False
			assert e.response["error"]
	else:
		try:
			response = client.chat_postEphemeral(
				channel=channel_id,
				text="残念！\n" + wrong_answer,
				user=user
			)
		except SlackApiError as e:
			# You will get a SlackApiError if "ok" is False
			assert e.response["error"]


def record_answer(user, row, user_answer: str, list_user):
	service = getGoogleService()
	answer_str = convert_choice(user_answer)
	list_user = list_user + "@" + user + "\n"
	spread_request = service.spreadsheets().values().clear(
		spreadsheetId=RECORD_ANSWER, range=answer_str + row)
	spread_request.execute()
	spread_request = service.spreadsheets().values().append(
		spreadsheetId=RECORD_ANSWER, range=answer_str + row,
		insertDataOption="OVERWRITE",
		valueInputOption="RAW", body={"values": [[list_user]]})
	spread_request.execute()


def convert_choice(user_answer):
	answer_list = ["E", "F", "G", "H", "I", "J", "K", "L"]
	return answer_list[int(user_answer) - 1]





if __name__ == "__main__":
	print("hi")
# data = \
# 	get_list(RECORD_ANSWER, "A" + str(2) + ":L" + str(2))["valueRanges"][0][
# 		"values"][0]
# correct_answer = data[1]
# print(has_answered("user", data[4:]))
# print(correct_answer)
# print(data)
# print(convert_choice("1"))
