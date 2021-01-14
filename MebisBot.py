import asyncio
import discord
import os
import re
import requests
import time
import shutil
import sys
from discord.ext import commands 
from threading import Thread

testcalender = "calendar.ics"
userFile = "database/user.ls"


#get the calendar URL from a user
def getCalendarFromUser(user):
    #saves file content to list
    file = open(userFile)
    lines = file.readlines()
    file.close
    calendarURL = ""
    #searches for the user
    for line in lines:
        if re.search("user:" + user, line):
            calendarURL = line.replace("{user:"+user+", calendarURL:", "")
            calendarURL = calendarURL.replace("}", "")
    return calendarURL

#downloads a Calendar from mebis
def downloadCalendar(user, path):
    #gets URL
    calendarURL = getCalendarFromUser(user)
    #download file
    r = requests.get(calendarURL)
    #save to file
    file = open(path, "w")
    file.write(r.text)
    file.close

def removeUser(user):
    #loads the file to a list
    file = open(userFile)
    lines = file.readlines()
    file.close

    #clears the file
    file = open(userFile, "w")
    file.write("")
    file.close()
    #reopens it for appending
    file = open(userFile, "a")

    #goes through every line and if the user is found, this line is not added
    first = True
    for line in lines:
        line = line.replace("\n", "")
        if not first:
            line = "\n"+line
        if not re.search("user:"+user, line):
            file.write(line)            
            first = False
    file.close()
    #remove the saved calendar file if existing
    if os.path.exists("database/icsfiles/" + user + ".ics"):
        os.remove("database/icsfiles/" + user + ".ics")
    
    
def configUser(user, calendarURL):
    removeUser(user)
    #opens file for reading once
    file = open(userFile)
    line = file.readline()
    file.close
    #reopens it for appending
    file = open(userFile, "a")
    #creates the string to append the file
    lineOut = "{user:" + user + ", calendarURL:" + calendarURL + "}" 
    #if the file already contains something, append it
    if re.search("{",line) :
        file.write("\n" + lineOut)
    else:
        file.write(lineOut)
    file.close

#loads ics files to a array and returns it
def readIcsFile(filename):
    #opens the ics file
    file = open(filename)

    #creates a list to save the important data form the Calendar
    eventList = []

    #loads the file to a array
    lines = file.readlines()
    #closes file
    file.close

    #creates a dummy list for a later insert to the event list
    cacheLs = ["no summary", "no description", "no date specified", "no category"]

    #processes every line 
    for i in range(0, len(lines)):
        line = lines[i]
        line = line.replace("\n", "")
        line = line.replace("\\n", "")
        line = line.replace("\\", "")
        line = line.replace("\t", "")
        #if the line contains "SUMMARY" it replaces the Summary placeholder 
        if re.search("SUMMARY:",line):
            line = line.replace("SUMMARY:", "", 1)
            cacheLs[0] = line
        #if the line contains "DESCRIPTION" it replaces the description placeholder 
        elif re.search("DESCRIPTION:",line):
            line = line.replace("DESCRIPTION:", "", 1)
            description = line
            line = file.readline()
            #if the line contains "CLASS" it stopps adding to the description 
            while not re.search("CLASS:",line):
                #removes formatting operators from the text
                line = line.replace("\n", "")
                line = line.replace("\\n", "")
                line = line.replace("\\", "")
                line = line.replace("\t", "")

                description += line
                i += 1
                line = lines[i]
            if description != "":
                cacheLs[1] = description
        #if the line contains "DTSTART" it replaces the date placeholder 
        elif re.search("DTSTART:",line):
            line = line.replace("DTSTART:", "", 1)
            cacheLs[2] = line
        #if the line contains "CATEGORIES" it replaces the category placeholder 
        elif re.search("CATEGORIES:",line):
            line = line.replace("CATEGORIES:", "", 1)
            cacheLs[3] = line
        #if the line contains a "END" statement, the the chache list is added to the eventlist and is cleared
        elif re.search("END:VEVENT",line):
            eventList.append(cacheLs)
            #replaces the cache with a dummy again
            cacheLs = ["no summary", "no description", "no date specified", "no category"]
    return eventList

#returns a array of all noted users
def getAllUser():
    #saves file content
    file = open(userFile)
    lines = file.readlines()
    file.close()
    users = []
    #goes through every line
    for line in lines:
        user = ""
        #removes everything but the user-id
        for i in range(6, len(line)):
            #stopps if a comma occurs, since it seperates the user from the calendarURL
            if line[i] == ',':
                break
            user += line[i]
        users.append(user)
    return users

def convertIcsDate(date):
    #converts the date format used in ICS to dd.mm.yyyy hh.MM (ignoring sceonds)
    year = date[0:4]
    month = date[4:6]
    day = date[6:8]
    hour = int(date[9:11]) + 1
    minute = date[11:13]
    return day +"."+ month + "." + year + "   " + str(hour) + ":" + minute 

bot = commands.Bot(command_prefix = '>')
run = True
async def updateMebisCalendar():
    while run:
        #stores all users
        users = getAllUser()
        #works through every user
        for u in users:
            print("checking calender of " + u)
            #downloads calender in the cache folder
            downloadCalendar(u, "database/icsfiles/temp.ics")
            #loads new ICS calendar file
            uCalNew = readIcsFile("database/icsfiles/temp.ics")
            try:
                #loads old ICS calendar file
                uCalOld = readIcsFile("database/icsfiles/" + u + ".ics")
            except:
                #if it fails, make it a table which is never returned by readIcsFile()
                uCalOld = ["error"]
            #if its not the same
            if uCalNew != uCalOld:

                found = False
                embed = discord.Embed(
                    title="neuer Mebis Termin",
                    url="https://lernplattform.mebis.bayern.de/my/",
                    color=0x0786d5,
                    description="dein Mebis Kalender wurde Aktualisiert!"
                )
                #go through every new Event
                for event in uCalNew:
                    #and if its not noted yet notify the user
                    if uCalOld.count(event) == 0:
                        #remember that sth was found
                        found = True
                        #add a field to the embed
                        embed.add_field(name=event[3], value="Kurzbeschreibung: " + event[0] + "\n" + event[1] + "\n Am:" + convertIcsDate(event[2]), inline=False)
                #only send it if the changes were found
                if found:
                    print("notifying "+ u +"...")
                    await bot.get_channel(int(u)).send(embed=embed)

                #notify the user
                #save the new Calendar
                shutil.copyfile("database/cache/" + u + ".ics", "database/icsfiles/" + u + ".ics")
                #delete the file from the cache
                os.remove("database/icsfiles/temp.ics")
        print("done")
        #pause loop for a time in seconds
        await asyncio.sleep(10*60)
        print("updating")
        


@bot.event
async def on_ready():
    print("ready")
    await updateMebisCalendar()


@bot.command(name="configUser", help="ordnet dem Kanal einen Mebis-Kalender Link zu.\n Snytax: >configUser [URL]\n um den URL deines Mebiskalenders zu finden, nutze >calendarHelp")
async def confUser(ctx):
#search for the position mebis calendar URL
    try:
        matchspan = re.search("https://lernplattform.mebis.bayern.de/calendar/export_execute.php\?userid=.+\&authtoken=.+&preset_what=.+&preset_time=.+", ctx.message.content).span()
    except:
    #if no URL is found, notify the user
        await ctx.send("es wurde kein korrekter Link zu einem Mebis Kalender gefunden.\n" + 
                        "Syntax: >configUser [URL des Mebiskalender]\n"+
                        "Anleitung für das anfordernd des Kalender links: >calendarHelp")
        return
    
    #save the channel ID as user and cut the URL out of the 
    configUser(str(ctx.message.channel.id), ctx.message.content[matchspan[0]:matchspan[1]])

    await ctx.send("registriert!")

@bot.command(name="calendarHelp", help="Anleitung um die URL deines Mebiskalenders zu finden")
async def calendarHelp(ctx):
    embed=discord.Embed(title="Mebis Kalender Exportieren:", color=0x0786d5)
    embed.set_author(name="Mebis Kalender", 
        url="https://lernplattform.mebis.bayern.de/calendar/view.php?view=month",
        icon_url="https://ofr.bdb-gym.de/wp-content/uploads/2019/10/mebis-logo-quadrat.png")
    embed.add_field(name="1.", value="klicke oben auf \"Mebis Kalender\"", inline=False)
    embed.add_field(name="2.", value="gehe auf \"Kalender exportieren\" am unteren Rand", inline=True)
    embed.add_field(name="3.", value="wähle nun deine Bevorzugten einstellungen (empfohlen: \"Alle Termine\" & \"Vergangene und nachfolgende 60 Tage\")", inline=True)
    embed.add_field(name="4.", value="wenn du nun auf \"Kalender-URL abfragen\" drückst, wird dir deine Kalender-URL angezeigt.", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="removeUser", help="entferne dich von der Aktualisierungsliste")
async def remUser(ctx):
    removeUser(str(ctx.message.channel.id))
    await ctx.send("dieser Channel (" + str(ctx.message.channel.id) + ") wurde von der Liste entfernt")

bot.run("discord_bot_token")
