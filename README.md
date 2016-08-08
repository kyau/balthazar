## Balthazar MajorMUD Bot

:warning: This is a work in progress, please report any issues!

[About Balthazar](#about-balthazar)

[Features](#features)

[Installation](#installation)


### About Balthazar

Balthazar aims to be the swiss army knife of MajorMUD realm bots. Written in
Python and easily configurable this bot can bring life to your otherwise
lifeless realm. We all know that MajorMUD is not exactly a newer game nor does
it bring with it any advanced forms of technology to tap into its data. For
this I present to you Balthazar.

### Features

While running Balthazar you will be able to provide the following services
in-game to other players via your bot.

- [ ] Alignment resets
- [ ] Add Lives to players
- [ ] Monster status

In addition to the in-game services provided Balthazar will also be able to
dump in-game data into a MySQL database. The following will all be recorded:

- [x] Who's Online
- [x] List of Top 100 Users
- [x] List of Top 100 Gangs
- [x] Tracking EXP/Hour for Users and Gangs

### Installation

To install Balthazar you will need Python 3.5+ and the Python module
[MySQLdb](http://mysql-python.sourceforge.net/). You will need to create the
database structure located in `mysql.txt`. You will then need to edit the
`bbs.cfg` and place it in the parent directory of the script location.
(eg. if the script is in `/home/kyau/balthazar`, then the `bbs.cfg` needs to be
located in `/home/kyau`).