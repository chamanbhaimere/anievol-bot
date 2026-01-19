FROM python:3.10-slim-bullseye

#Dont Remove My Credit @AV_BOTz_UPDATE 
#This Repo Is By @BOT_OWNER26 
# For Any Kind Of Error Ask Us In Support Group @AV_SUPPORT_GROUP

RUN apt-get update && apt-get upgrade -y && apt-get install -y git
COPY requirements.txt /requirements.txt

#Dont Remove My Credit @AV_BOTz_UPDATE 
#This Repo Is By @BOT_OWNER26 
# For Any Kind Of Error Ask Us In Support Group @AV_SUPPORT_GROUP

RUN cd /
RUN pip3 install -U pip && pip3 install -U -r requirements.txt
RUN mkdir /AV_FILE_TO_LINK
WORKDIR /AV_FILE_TO_LINK
COPY . /AV_FILE_TO_LINK

#Dont Remove My Credit @AV_BOTz_UPDATE 
#This Repo Is By @BOT_OWNER26 
# For Any Kind Of Error Ask Us In Support Group @AV_SUPPORT_GROUP

CMD ["python", "bot.py"]
