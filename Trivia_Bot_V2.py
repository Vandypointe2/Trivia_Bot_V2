from twitchio.ext import commands
import random
#from dotenv import load_dotenv
import os
import gspread
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict
import openai
import json

#load_dotenv()


class Bot(commands.Bot):

    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        global trivia_switch,gpt_switch,credentials,gc,channel,bot_token,translate_flag,client_id,clip_api_authorization,broadcaster_id
        credentials_json =os.getenv('CREDS')
        openai.api_key=os.getenv('API_KEY')
        channel = os.getenv('CHANNEL')
        bot_token=os.getenv('BOT_TOKEN')
        
        
        #client_id=os.getenv('CLIENT_ID')
        #broadcaster_id=os.getenv('BROADCASTER_ID')
        #clip_api_authorization=os.getenv('AUTH')
        #broadcaster_id='58187542'

        
        super().__init__(token=bot_token, prefix='!', initial_channels=[channel],case_insensitive=True)
        self.questions_and_answers = []
        self.user_scores = {}
        trivia_switch=1
        gpt_switch=1
        translate_flag=1
        credentials = json.loads(credentials_json)
        gc = gspread.service_account_from_dict(credentials)
        
    async def event_ready(self):
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
        self.load_data()
        # Start the scheduling task
        loop = asyncio.get_event_loop()
        loop.create_task(self.autosave_score_schedule_function())
        # Run the event loop
        #loop.run_forever()

    async def event_message(self, ctx):
        'Runs every time a message is sent in chat.'
        # Make sure the bot processes commands first
        await self.handle_commands(ctx)
        if translate_flag == 0:
            return

        # Make sure the bot ignores itself and the streamer
        if ctx.author.name.lower() == self.nick.lower():
             return
        chattername=ctx.author.name
        # You might want to add additional conditions here if you don't want to echo every message
        if not ctx.content.startswith('!'):
            # Prepare the messages for OpenAI Chat model
            messages = [
                {"role": "system", "content": (
                    "You are a bot that Translates any other languages to English, When you are given text to translate it, Check what language the text is. If it is english then just respond with ENG, otherwise translate the text you were given to english and only send that back as the response. ")},
                {"role": "user", "content": ctx.content}
            ]

            # Call OpenAI API
            try:
                openai_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                # Process OpenAI's response
                ai_answer = openai_response.choices[0].message['content'].strip().lower()
                print(ai_answer+" message sent by "+chattername)
                if ai_answer=='eng':
                    return
                else:
                    response = ai_answer

            except Exception as e:
                response = f"Error With Translating: {e}"

        await ctx.channel.send(chattername+" said: "+response)
                


    async def auto_score_saver(self):
        score_sheet = gc.open(f"{channel} score sheet").sheet1  # Replace with your sheet name
            
            # Retrieve the existing scores from the Google Sheet
        existing_scores = score_sheet.get_all_records()
        score_dict = {row['User']: int(row['Score']) for row in existing_scores}
            
            # Update scores in the dictionary
        for user, score in self.user_scores.items():
                if user in score_dict:
                    if score > score_dict[user]:
                        score_dict[user] = score
                    elif score < score_dict[user]:
                        score_dict[user] += score
                else:
                    score_dict[user] = score

            # Clear the existing data in the Google Sheet
        score_sheet.clear()
            
            # Write the updated scores to the Google Sheet
        updated_scores = [['User', 'Score']]
        for user, score in score_dict.items():
                updated_scores.append([user, score])
        score_sheet.update(updated_scores)
            
            # Update the scores dictionary with the updated scores
        self.user_scores = score_dict
        print('Scores Saved Automatically')


    async def autosave_score_schedule_function(self):
        while True:
            # Call your function to save the scores
            await self.auto_score_saver()
            

            # Wait for 1 minutes
            await asyncio.sleep(60)  # 10 minutes = 600 seconds



    def load_data(self):
        global currentAnswer, currentQuestion, gc
        currentAnswer = None
        currentQuestion = None
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        gc = gspread.service_account_from_dict(credentials)
        sheet = gc.open('TriviaDataset').sheet1
        data = sheet.get_all_records()
        self.questions_and_answers = [(row['Question'], row['Answer']) for row in data if row['Question'] and row['Answer']]
        score_sheet = gc.open(f"{channel} score sheet").sheet1  # Replace with your sheet name
        data = score_sheet.get_all_values()
        for row in data[1:]:  # Exclude the header row
            self.user_scores[row[0]] = int(row[1])
        
        print('Scores loaded!')

    
    @commands.command(name='LoadQuestions')
    async def load_questions_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            global currentAnswer, currentQuestion
            currentAnswer = None
            currentQuestion = None
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            sheet = gc.open('TriviaDataset').sheet1
            data = sheet.get_all_records()
            self.questions_and_answers = [(row['Question'], row['Answer']) for row in data if row['Question'] and row['Answer']]
            await ctx.send("Questions Loaded!")
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")


    @commands.command(name='GPTOn')
    async def gpt_on_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            global gpt_switch
            gpt_switch = 1
            print(f"gpt_switch value: {gpt_switch}")
            await ctx.send("GPT is now On")
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")

    @commands.command(name='Translator')
    async def translator_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            global translate_flag
            translate_flag = 1 if translate_flag == 0 else 0
            print(f"Translator value: {translate_flag}")
            await ctx.send(f"Translator is now {'On' if gpt_switch == 1 else 'Off'}")
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")


    @commands.command(name='TriviaTurnOn')
    async def trivia_on_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            global trivia_switch
            trivia_switch = 1
            print(f"trivia_switch value: {trivia_switch}")
            await ctx.send("Trivia is now On")
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")

    @commands.command(name='TriviaTurnOff')
    async def trivia_off_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            global trivia_switch
            trivia_switch = 0
            print(f"trivia_switch value: {trivia_switch}")
            await ctx.send("Trivia Is now Off")
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")
    
    @commands.command(name='GPTOff')
    async def gpt_off_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            global gpt_switch
            gpt_switch = 0
            print(f"gpt_switch value: {gpt_switch}")
            await ctx.send("GPT is now Off")
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")

    @commands.command(name='SwitchValue')
    async def switch_value_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            await ctx.send(f"Trivia Switch is {str(trivia_switch)}")
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")

    @commands.command(name='CurrentAnswer')
    async def current_answer_call(self, ctx):
        global currentAnswer
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            await ctx.send(currentAnswer)
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")

    @commands.command(name='CurrentQuestion')
    async def current_question_call(self, ctx):
        global currentQuestion, currentAnswer, trivia_switch
        if trivia_switch==1:
            if not currentQuestion:
                
                    currentQuestion, answer = random.choice(self.questions_and_answers)
                    currentAnswer = str(answer)
                    await ctx.send(currentQuestion)
            else:
                await ctx.send(currentQuestion)
        else:
            await ctx.send("Trivia is turned off at the moment, ask the channel owner to turn it on.")

    @commands.command(name='Guess')
    async def guess_command(self, ctx: commands.Context, *, guess_text: str):
        global currentAnswer
        global currentQuestion

        if not currentAnswer:
            response = f"Sorry {ctx.author.name}! There is no trivia question to guess for right now! Type !CurrentQuestion to start a new round!"
        else:
            # Prepare the messages for OpenAI Chat model
            messages = [
                {"role": "system", "content": (
                    "You are a bot that compares a trivia guess to the correct answer. "
                    "If the guess is close enough to the correct answer or there is just a simple misspelling, respond with 'Correct'. "
                    "If the guess is not close enough or the spelling is too far wrong from the correct answer, respond with 'Incorrect'.")},
                {"role": "user", "content": f"Trivia question: \"{currentQuestion}\". User guess: \"{guess_text}\". Correct answer: \"{currentAnswer}\"."}
            ]

            # Call OpenAI API
            try:
                openai_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                print(currentQuestion,', ',guess_text,', ',currentAnswer)
                # Process OpenAI's response
                ai_answer = openai_response.choices[0].message['content'].strip().lower()
                print(ai_answer)
                if ai_answer=='correct':
                    # Logic to update score if the answer is correct
                    if ctx.author.name not in self.user_scores:
                        self.user_scores[ctx.author.name] = 1
                    else:
                        self.user_scores[ctx.author.name] += 1

                    response = f"Correct, {ctx.author.name}! The answer was -{currentAnswer}-, Your score is now {self.user_scores[ctx.author.name]}."
                    currentAnswer = None
                    currentQuestion = None
                else:
                    response = f"Incorrect, {ctx.author.name}! Your score remains {self.user_scores.get(ctx.author.name, 0)}."

            except Exception as e:
                response = f"Error processing your guess: {e}"

        await ctx.send(response)

    @commands.command(name='Score')
    async def score_command(self, ctx: commands.Context):
        if ctx.author.name in self.user_scores:
            await ctx.send(f"{ctx.author.name}, your score is {self.user_scores[ctx.author.name]}.")
        else:
            await ctx.send(f"{ctx.author.name}, you haven't answered any questions correctly since the last save")
    
    @commands.command(name='Ask')
    async def ask_command(self, ctx: commands.Context, *, ask_text: str):
    
            if gpt_switch==1:
                # Prepare the messages for OpenAI Chat model
                messages = [
                    {"role": "system", "content": (
                        "You are a bot that users ask questions to, do your best to answer the questions as accurately and helpfully as possible about what they ask for, but try to keep the answers decently short and compact. Aim for about 3 sentences. If you think that the question is inappropriate, respond with: That request is inappropriate and I will not be able to answer that.  ")},
                    {"role": "user", "content": ask_text}
                ]
                openai_response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=messages
                    )
                    # Process OpenAI's response
                ai_answer = openai_response.choices[0].message['content'].strip()
                print(ask_text)
                print(ai_answer)
                await ctx.send(ai_answer)
            else:
                await ctx.send("ChatGPT is turned off at the moment, ask the channel owner to turn it on.")

    @commands.command(name='TriviaHelp')
    async def help_command(self, ctx):
        help_text = f"Hello {ctx.author.name}, Go here to get help: http://notepad.link/share/UqD07nYptBf3wQqta73o"
        # https://notepad.link/fZDFp Is the editable note link for the above
        await ctx.send(help_text)

    @commands.command(name='TriviaSkip')
    async def trivia_mod_command(self, ctx):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            global currentQuestion
            currentQuestion = None
            await self.current_question_call(ctx)
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")

    @commands.command(name='SaveScores')
    async def update_score_command(self, ctx: commands.Context):
        if ctx.author.is_mod or ctx.author.name == ctx.channel.name:
            # Open the Google Sheet
            score_sheet = gc.open(f"{channel} score sheet").sheet1  # Replace with your sheet name
            
            # Retrieve the existing scores from the Google Sheet
            existing_scores = score_sheet.get_all_records()
            score_dict = {row['User']: int(row['Score']) for row in existing_scores}
            
            # Update scores in the dictionary
            for user, score in self.user_scores.items():
                if user in score_dict:
                    if score > score_dict[user]:
                        score_dict[user] = score
                    elif score < score_dict[user]:
                        score_dict[user] += score
                else:
                    score_dict[user] = score

            # Clear the existing data in the Google Sheet
            score_sheet.clear()
            
            # Write the updated scores to the Google Sheet
            updated_scores = [['User', 'Score']]
            for user, score in score_dict.items():
                updated_scores.append([user, score])
            score_sheet.update(updated_scores)
            
            # Update the scores dictionary with the updated scores
            self.user_scores = score_dict
            await ctx.send('Scores Saved!')
        else:
            await ctx.send("Sorry, only mods and the channel owner can run this command.")


    @commands.command(name='Top10')
    async def top10_command(self, ctx: commands.Context):
        sorted_users = sorted(self.user_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        response = "Top 10 Users: \n"
        for i, (user, score) in enumerate(sorted_users):
            response += f" {i+1}. {user}:  {score} points|\n"
        await ctx.send(response) 

    @commands.command(name='Hint')
    async def hint_command(self, ctx: commands.Context):
        global currentAnswer
        hint = ''
        for char in currentAnswer:
            if char == ' ':
                hint += ' '
            else:
                if random.random() <= 0.5:
                    hint += '_'
                else:
                    hint += char
        await ctx.send(f"The hint for the answer is: {hint}")


    # @commands.command(name='getclips')
    # async def fetch_clips(self, ctx):
    #     """Fetch top clips for a broadcaster."""
    #     url = f"https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}&first=10"
    #     headers = {
    #         'Client-ID': client_id,
    #         'Authorization': f'Bearer {clip_api_authorization}'
    #     }
    #     # Make the HTTP request to Twitch API
    #     response = requests.get(url, headers=headers)
    #     if response.status_code == 200:
    #         clips = response.json().get('data', [])
    #         if clips:
    #             # Formatting the clip information
    #             clip_details = '\n'.join([f"{clip['title']} - {clip['url']}" for clip in clips])
    #             await ctx.send(f"Top clips:\n{clip_details}")
    #         else:
    #             await ctx.send("No clips found.")
    #     else:
    #         await ctx.send("Failed to fetch clips.")
    #         print(response)
    
        

    
bot = Bot()
bot.run()


