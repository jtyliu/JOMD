# JOMD
JOMD is a Discord bot for [Dmoj](https://dmoj.ca/)

# Features
The current set of features are limited, although more are planned to be added.

### user
Show user profile with recent submissions

### predict
Predict culminated points after solving a problems with some amount of points

### gimme
Problem suggestion with point range filter and problem type filter

### plot type
Shows a radar chart of problems solved by users

# Setup

To setup the bot first clone the repository and cd into it

```
git clone https://github.com/JoshuaTianYangLiu/JOMD.git
cd JOMD
```


Make sure you have python3.7 installed.

```
apt-get install python3.7
```

Install relevant packages

```
pip3.7 install -r requirements.txt
```

Add your discord bot token with

```
export JOMD_BOT_TOKEN="INSERT BOT TOKEN HERE"
```

If you also want to add your DMOJ api token use

```
export JOMD_TOKEN="INSERT DMOJ API TOKEN HERE"
```

Run the bot with

```
python3.7 Main.py
```

# Usage
To use the bot, use the `+` prefix

# Contributing
Pull requests are welcomed and encouraged.
