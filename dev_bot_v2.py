import discord
import sqlite3 as sl
import os
import var
import random
import numpy as np
import cv2
import urllib
from Card import Card

#Set up the database connection
con = sl.connect('my-test.db')

#Set up variables from the config file
TOKEN = var.token
start_game_image = var.start_game_image
emoji_to_num = var.emoji_to_num
num_to_emoji = var.num_to_emoji

#Set up Discord connection
intents = discord.Intents.all()
client = discord.Client(intents=intents)

#Set up variables for use in the program
verbose = True
awaiting_reaction = {}
game_start_message_to_game_id = {}
game_id_to_game_set_packs = {}
messages_queued_for_deletion = []
whitelisted_channels = []


################    INNER FUNCTIONS    ################

#Used to generate a reference string for the passed user
def reference_user(user):
    return "<@" + str(user.id) + ">"

#Used to generate a reference string for the passed user_id
def reference_user_by_id(id):
    return "<@" + str(id) + ">"

#Runs SQL statement and returns the rows
def run_sql(sql_stmt):
    if verbose == True:
        print(sql_stmt)
    results = con.execute(sql_stmt)
    rows = results.fetchall()
    return rows

def get_random_card_of_rarity(game, set_acro, rarity):
    sql_stmt = """
        select card_id 
        from cards where card_id =
        (
            select card_id from 
            (
                select card_id
                , row_number() over (order by card_id) as choice 
                from cards 
                where game = '""" + game + """' 
                and set_acro = '""" + set_acro + """' 
                and rarity = '""" + rarity + """' 
                and active_flag = 'Y'
            ) x
            where x.choice = 
            (
                select 
                (
                    abs
                    (
                        random() % 
                        (
                            select count(*) 
                            from cards 
                            where 
                            game = '""" + game + """'
                            and set_acro = '""" + set_acro + """' 
                            and rarity = '""" + rarity + """' 
                            and active_flag = 'Y'
                        )
                    ) + 1
                ) as choice
            )
        )"""
    rows = run_sql(sql_stmt)
    for row in rows:
        card_id = row[0]
    return card_id

def get_next_pack_id():
    sql_stmt = """select ifnull(max(pack_id), 0) + 1 as pack_id from packs"""
    rows = run_sql(sql_stmt)
    for row in rows:
        pack_id = row[0]
    return pack_id

def get_next_pack_card_id_for_pack(pack_id):
    sql_stmt = """select ifnull(max(pack_card_id), 0) + 1 as pack_card_id from packs where pack_id = """ + str(pack_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        pack_card_id = row[0]
    return pack_card_id

def get_booster_meta_data(game, set_acro):
    sql_stmt = """select cards_per_pack
    ,c_per_pack
    ,u_per_pack
    ,r_per_pack
    ,r_weight
    ,r2_weight
    ,r3_weight
    from booster_sets where game = '""" + game + """' and set_acro = '""" + set_acro + """';"""
    rows = run_sql(sql_stmt)
    for row in rows:
        cards_per_pack = row[0]
        c_per_pack = row[1]
        u_per_pack = row[2]
        r_per_pack = row[3]
        r_weight = row[4]
        r2_weight = row[5]
        r3_weight = row[6]
    return {
    "cards_per_pack": cards_per_pack
    ,"c_per_pack": c_per_pack
    ,"u_per_pack": u_per_pack
    ,"r_per_pack": r_per_pack
    ,"r_weight": r_weight
    ,"r2_weight": r2_weight
    ,"r3_weight": r3_weight}

def insert_card_into_pack(pack_id, pack_card_id, set_acro, card_id):
    sql_stmt = """
        insert into packs (pack_id, pack_card_id, set_acro, card_id, taken_flag)
        values
        (
            """ + str(pack_id) + """
            ,""" + str(pack_card_id) + """
            ,'""" + set_acro + """'
            ,""" + str(card_id) + """
            ,'N'
        )"""
    run_sql(sql_stmt)
    con.commit()

def generate_pack(game, set_acro):
    pack_id = get_next_pack_id()
    booster_meta_data_dict = get_booster_meta_data(game, set_acro)
    card_ids = []
    i = 0
    if booster_meta_data_dict["c_per_pack"] > 0:
        while i < booster_meta_data_dict["c_per_pack"]:
            pack_card_id = get_next_pack_card_id_for_pack(pack_id)
            card_id = get_random_card_of_rarity(game, set_acro, "C")
            if card_id not in card_ids:
                insert_card_into_pack(pack_id, pack_card_id, set_acro, card_id)
                i = i + 1
                card_ids.append(card_id)
    i = 0
    if booster_meta_data_dict["u_per_pack"] > 0:
        while i < booster_meta_data_dict["u_per_pack"]:
            pack_card_id = get_next_pack_card_id_for_pack(pack_id)
            card_id = get_random_card_of_rarity(game, set_acro, "U")
            if card_id not in card_ids:
                insert_card_into_pack(pack_id, pack_card_id, set_acro, card_id)
                i = i + 1
                card_ids.append(card_id)
    i = 0
    if booster_meta_data_dict["r_per_pack"] > 0:
        while i < booster_meta_data_dict["r_per_pack"]:
            pack_card_id = get_next_pack_card_id_for_pack(pack_id)
            card_id = get_random_card_of_rarity(game, set_acro, "R")
            if card_id not in card_ids:
                insert_card_into_pack(pack_id, pack_card_id, set_acro, card_id)
                i = i + 1
                card_ids.append(card_id)
    roll = random.randint(1, booster_meta_data_dict["r_weight"] + booster_meta_data_dict["r2_weight"] + booster_meta_data_dict["r3_weight"])
    if roll < booster_meta_data_dict["r3_weight"]:
        pack_card_id = get_next_pack_card_id_for_pack(pack_id)
        card_id = get_random_card_of_rarity(game, set_acro, "R3")
        insert_card_into_pack(pack_id, pack_card_id, set_acro, card_id)
    elif roll < booster_meta_data_dict["r2_weight"]:
        pack_card_id = get_next_pack_card_id_for_pack(pack_id)
        card_id = get_random_card_of_rarity(game, set_acro, "R2")
        insert_card_into_pack(pack_id, pack_card_id, set_acro, card_id)
    else:
        pack_card_id = get_next_pack_card_id_for_pack(pack_id)
        card_id = get_random_card_of_rarity(game, set_acro, "R")
        insert_card_into_pack(pack_id, pack_card_id, set_acro, card_id)
    return pack_id

def get_cards(pack_id):
    sql_stmt = """
        select 
            c.name
            ,c.set_acro|| '-'|| substr('000' || cast(c.set_number as text), -3, 3) as set_acro_plus_number
            ,c.card_img_url
            ,p.pack_card_id
            ,p.pack_id
        from packs p
        join cards c
        on c.card_id = p.card_id
        and p.pack_id = """ + str(pack_id) + """
        and p.taken_flag = 'N'
        order by rarity"""
    rows = run_sql(sql_stmt)
    cards = []
    for row in rows:
        mycard = Card(row[0], row[1], row[4], row[3], row[2])
        cards.append(mycard)
    return cards

def get_next_game_id():
    sql_stmt = """select ifnull(max(game_id), 0) + 1 as game_id from games"""
    rows = run_sql(sql_stmt)
    for row in rows:
        game_id = row[0]
    return game_id

def add_player_to_game(player_id, game_id, seat_number):
    sql_stmt = """select count(*) as cnt from games where game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        num_game_rows = row[0]
    if num_game_rows < 1 :
        sql_stmt = """insert into games
            (
                game_id
                , seat_number
                , player_id
                , assigned_pack
                , pick_num
                , goal_pick_num
                , open_for_players
            )
            values
            (
                """ + str(game_id) + """
                ,""" + str(seat_number) + """
                ,""" + str(player_id) + """
                ,null
                ,0
                ,0
                ,'Y'
            );
        """
        run_sql(sql_stmt)
        con.commit()
        return "Game " + str(game_id) + " opened!\nAdded player " + reference_user_by_id(player_id) + " to Game " + str(game_id) + " in seat number " + str(seat_number)
    else:
        sql_stmt = """select count(distinct seat_number) from games where game_id = """ + str(game_id) + """ and player_id = """ + str(player_id) + """;"""
        rows = run_sql(sql_stmt)
        for row in rows:
            seats_already_filled = row[0]
            print(str(seats_already_filled))
        if seats_already_filled > 0:
            sql_stmt = """select distinct seat_number from games where game_id = """ + str(game_id) + """ and player_id = """ + str(player_id) + """;"""
            rows = run_sql(sql_stmt)
            for row in rows:
                seats_filled = row[0]
            return "Player " + reference_user_by_id(player_id) + " already occupies seat(s) " + str(seats_filled)
        sql_stmt = """select max(open_for_players) from games where game_id = """ + str(game_id) + """;"""
        rows = run_sql(sql_stmt)
        for row in rows:
            open_for_players = row[0]
        if open_for_players == 'N':
            return "Game " + str(game_id) + " is not currently accepting players"
        else:
            sql_stmt = """select count(*) from games where game_id = """ + str(game_id) + """ and seat_number = """ + str(seat_number) + """;"""
            rows = run_sql(sql_stmt)
            for row in rows:
                players_in_requested_seat = row[0]
            if players_in_requested_seat > 0:
                sql_stmt = """select player_id from games where game_id = """ + str(game_id) + """ and seat_number = """ + str(seat_number) + """;"""
                rows = run_sql(sql_stmt)
                for row in rows:
                    player_in_requested_seat = row[0]
                return "Player " + reference_user_by_id(player_in_requested_seat) + " is already in the requested seat number " + str(seat_number)
            else:
                sql_stmt = """insert into games
                (
                    game_id
                    , seat_number
                    , player_id
                    , assigned_pack
                    , pick_num
                    , goal_pick_num
                    , open_for_players
                )
                values
                (
                    """ + str(game_id) + """
                    ,""" + str(seat_number) + """
                    ,""" + str(player_id) + """
                    ,null
                    ,0
                    ,0
                    ,'Y'
                );
                """
                run_sql(sql_stmt)
                con.commit()
                return "Added player " + reference_user_by_id(player_id) + " to Game " + str(game_id) + " in seat number " + str(seat_number)

def choose_unopened_pack(game_id):
    sql_stmt = """
    select y.pack_id
    from 
    (
        select abs
        (
        	random() % 
        	(
           	 	select count(distinct pack_id) 
           	 	from game_packs_lkp 
            	where game_id = """ + str(game_id) + """
                and pack_id not in 
                (
                    select ifnull(assigned_pack, -1) from games where game_id = """ + str(game_id) + """
                )
                and pack_id not in
                (
                    select distinct pack_id from packs where taken_flag = 'Y'
                )
        	)
       	) + 1 as choice
    ) x
    left join
    (
        select pack_id
        , row_number() over (order by pack_id) as pack_options 
        from game_packs_lkp 
        where game_id = """ + str(game_id) + """
        and pack_id not in 
        (
            select ifnull(assigned_pack, -1) from games where game_id = """ + str(game_id) + """
        )
        and pack_id not in
        (
            select distinct pack_id from packs where taken_flag = 'Y'
        )
    ) y
    on x.choice = y.pack_options"""
    rows = run_sql(sql_stmt)
    for row in rows:
        pack_id = row[0]
    return pack_id

def assign_pack_id_to_player(game_id, player_id, pack_id):
    sql_stmt = """update games set assigned_pack = """ + str(pack_id) + """ where game_id = """ + str(game_id) + """ and player_id = """ + str(player_id) + """;"""
    run_sql(sql_stmt)
    con.commit()

def get_number_of_players(game_id):
    sql_stmt = """select count(distinct seat_number) from games where game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        number_of_players = row[0]
    return number_of_players

def open_for_players(game_id):
    sql_stmt = """select max(open_for_players) from games where game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        open_for_players = row[0]
    if open_for_players == 'N':
        return False
    else:
        return True

def get_player_ids(game_id):
    player_ids = []
    sql_stmt = """select distinct player_id from games where game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        player_ids.append(row[0])
    return player_ids

def insert_into_game_packs_lkp(game_id, pack_id):
    sql_stmt = """insert into game_packs_lkp (game_id, pack_id) values (""" + str(game_id) + """, """ + str(pack_id) + """);"""
    run_sql(sql_stmt)
    con.commit()

def get_member_object_by_id_server(id, server):
    return server.get_member(id)

def get_assigned_pack_id(game_id, player_id):
    sql_stmt = """select assigned_pack from games where game_id = """ + str(game_id) + """ and player_id = """ + str(player_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        pack_id = row[0]
    return pack_id

def get_game_id_by_pack_id(pack_id):
    sql_stmt = """select game_id from game_packs_lkp where pack_id = """ + str(pack_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        game_id = row[0]
    return game_id

def player_can_draft_card(game_id, player_id):
    sql_stmt = """select case when pick_num >= goal_pick_num then 'N' else 'Y' end from games where game_id = """ + str(game_id) + """ and player_id = """ + str(player_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        if row[0] == 'Y':
            return True
        else:
            return False

def card_taken(pack_id, pack_card_id):
    sql_stmt = """select taken_flag from packs where pack_id = """ + str(pack_id) + """ and pack_card_id = """ + str(pack_card_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        taken_flag = row[0]
    if taken_flag == 'Y':
        return True
    else:
        return False

def add_card_to_cardpool(pack_card_id,pack_id,game_id,player_id):
    sql_stmt = """
        insert into card_pools
        select """ + str(game_id) + """
        , """ + str(player_id) + """
        ,card_id
        from packs
        where pack_id = """ + str(pack_id) + """
        and pack_card_id = """ + str(pack_card_id) + """;"""
    run_sql(sql_stmt)
    con.commit()

def increment_player_pick_num(player_id, game_id):
    sql_stmt = """update games set pick_num = pick_num + 1 where player_id = """ + str(player_id) + """ and game_id = """ + str(game_id) + """;"""
    run_sql(sql_stmt)
    con.commit()

def increment_player_goal_pick_num(player_id, game_id):
    sql_stmt = """update games set goal_pick_num = goal_pick_num + 1 where player_id = """ + str(player_id) + """ and game_id = """ + str(game_id) + """;"""
    run_sql(sql_stmt)
    con.commit()

def increment_player_goal_pick_num_all_players(game_id):
    player_ids = get_player_ids(game_id)
    for player_id in player_ids:
        increment_player_goal_pick_num(player_id, game_id)

def time_to_continue(game_id):
    sql_stmt = """select count(*) from games where pick_num != goal_pick_num and game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count == 0:
        return True
    else:
        return False

def assigned_packs_depleted(game_id):
    sql_stmt = """select count(*) 
        from packs 
        where taken_flag = 'N' 
        and pack_id in 
        (
            select assigned_pack 
            from games 
            where game_id = """ + str(game_id) + """
        );"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count > 0:
        return False
    else:
        return True

def all_packs_depleted(game_id):
    sql_stmt = """select count(*)
    from packs
    where taken_flag = 'N'
    and pack_id in
    (
        select pack_id
        from game_packs_lkp
        where game_id = """ + str(game_id) + """
    );"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count > 0:
        return False
    else:
        return True

def assign_players_unopened_packs(game_id):
    player_ids = get_player_ids(game_id)
    for player_id in player_ids:
        pack_id = choose_unopened_pack(game_id)
        assign_pack_id_to_player(game_id, player_id, pack_id)

def get_seat_number(player_id, game_id):
    sql_stmt = """select seat_number from games where game_id = """ + str(game_id) + """ and player_id = """ + str(player_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        seat_number = row[0]
    return seat_number

def get_next_rotation_direction(game_id):
    sql_stmt = """select count(*) from games_direction_last_rotated where game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count == 0:
        sql_stmt = """insert into games_direction_last_rotated (game_id, direction) values (""" + str(game_id) + """, 'RIGHT');"""
        run_sql(sql_stmt)
        con.commit()
        return "RIGHT"
    else:
        sql_stmt = """select direction from games_direction_last_rotated where game_id = """ + str(game_id) + """;"""
        rows = run_sql(sql_stmt)
        for row in rows:
            last_direction = row[0]
        if last_direction == "RIGHT":
            new_direction = "LEFT"
        else:
            new_direction = "RIGHT"
        sql_stmt = """update games_direction_last_rotated set direction = '""" + new_direction + """' where game_id = """ + str(game_id) + """;"""
        run_sql(sql_stmt)
        con.commit()
        return new_direction

def get_seat_number_of_player_to_right(game_id, player_id):
    seat_number = get_seat_number(player_id, game_id)
    sql_stmt = """select count(*) from games where seat_number > """ + str(seat_number) + """ and game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count == 0:
        sql_stmt = """select min(seat_number) from games where game_id = """ + str(game_id) + """;"""
    else:
        sql_stmt = """select min(seat_number) from games where seat_number > """ + str(seat_number) + """ and game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        return row[0]

def get_seat_number_of_player_to_left(game_id, player_id):
    seat_number = get_seat_number(player_id, game_id)
    sql_stmt = """select count(*) from games where seat_number < """ + str(seat_number) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count == 0:
        sql_stmt = """select max(seat_number) from games where game_id = """ + str(game_id) + """;"""
    else:
        sql_stmt = """select max(seat_number) from games where seat_number < """ + str(seat_number) + """ and game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        return row[0]

def get_pack_id_by_seat_number(game_id, seat_number):
    sql_stmt = """select assigned_pack from games where seat_number = """ + str(seat_number) + """ and game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        pack_id = row[0]
    return pack_id

def get_rotation_direction(game_id):
    sql_stmt = """select count(*) from games_direction_last_rotated where game_id = """ + str(game_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count == 0:
        sql_stmt = """insert into games_direction_last_rotated (game_id, direction) values (""" + str(game_id) + """, 'RIGHT');"""
        run_sql(sql_stmt)
        con.commit()
        return "RIGHT"
    else:
        sql_stmt = """select direction from games_direction_last_rotated where game_id = """ + str(game_id) + """;"""
        rows = run_sql(sql_stmt)
        for row in rows:
            return row[0]

def rotate_assigned_packs(game_id):
    direction = get_rotation_direction(game_id)
    player_ids = get_player_ids(game_id)
    new_pack = {}
    for player_id in player_ids:
        seat_number = get_seat_number(player_id, game_id)
        if direction == "RIGHT":
            from_seat_number = get_seat_number_of_player_to_right(game_id, player_id)
        else:
            from_seat_number = get_seat_number_of_player_to_left(game_id, player_id)
        new_pack_id = get_pack_id_by_seat_number(game_id, from_seat_number)
        new_pack[player_id] = new_pack_id
    for player_id in player_ids:
        assign_pack_id_to_player(game_id, player_id, new_pack[player_id])

def set_pack_card_to_taken(pack_id, pack_card_id):
    sql_stmt = """update packs set taken_flag = 'Y' where pack_id = """ + str(pack_id) +  """ and pack_card_id = """ + str(pack_card_id) + """;"""
    run_sql(sql_stmt)
    con.commit()

def get_card_pool(game_id, player_id, game):
    final_output = ""
    sql_stmt = """select sql_stmt from decklist_format_sql where game = '""" + game + """';"""
    rows = run_sql(sql_stmt)
    for row in rows:
        sql_stmt = row[0]
    sql_stmt = sql_stmt.replace("<<game_id>>", str(game_id)).replace("<<player_id>>", str(player_id))
    rows = run_sql(sql_stmt)
    for row in rows:
        final_output = final_output + row[0] + '\n'
    return final_output

def add_channel_to_whitelist_in_db(channel):
    sql_stmt = """insert into whitelisted_channels (channel_id) values (""" + str(channel.id) + """);"""
    run_sql(sql_stmt)
    con.commit()

def load_whitelisted_channels_from_db():
    global whitelisted_channels
    sql_stmt = """select channel_id from whitelisted_channels;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        whitelisted_channels.append(client.get_channel(row[0]))

def remove_channel_from_whitelist_in_db(channel):
    sql_stmt = """delete from whitelisted_channels where channel_id = """ + str(channel.id) + """;"""
    run_sql(sql_stmt)
    con.commit()

def player_assigned_pack(player_id,pack_id,game_id):
    sql_stmt = """select count(*) from games where assigned_pack = """ + str(pack_id) + """ and game_id = """ + str(game_id) + """ and player_id = """ + str(player_id) + """;"""
    rows = run_sql(sql_stmt)
    for row in rows:
        count = row[0]
    if count == 0:
        return False
    else:
        return True

def write_card_pool_to_file(text, game_id, player_id):
    file_name = "Game_" + str(game_id) + "_PlayerID_" + str(player_id) + ".txt"
    f = open(file_name, "w")
    f.write(text)
    f.close()
    return file_name

def get_img_from_img_url(img_url):
    resp = urllib.request.urlopen(img_url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    return image
################    ASYNC FUNCTIONS    ################

async def clean(channel):
    messages = await channel.history().flatten()
    for message in messages:
        if isinstance(message.channel,discord.channel.DMChannel) and message.author == client.user:
            await message.delete()
        elif (not isinstance(message.channel,discord.channel.DMChannel)) and (message.author == client.user or message.content.startswith("$")):
            await message.delete()

async def send_current_pack(game_id,user):
    pack_id = get_assigned_pack_id(game_id, user.id)
    cards = get_cards(pack_id)
    card_choice = 0
    reaction_handler = {}
    final_content = ""
    images = []
    attempts = 0
    final_image_file_name = ""
    card_img_urls = ""
    for card in cards:
        card_choice = card_choice + 1
        choice_icon = num_to_emoji[card_choice]
        card_img_urls = card_img_urls + card.card_img_url + "\n"
        card_img = get_img_from_img_url(card.card_img_url)
        images.append(card_img)
        content = choice_icon + "  " + card.name + "  " + card.set_acro_plus_number + "\n"
        final_content = final_content + content
    while attempts < 20:
        try:
            final_image = cv2.vconcat(images)
            final_image_file_name = str(pack_id)+'.jpg'
            cv2.imwrite('./' + final_image_file_name, final_image)
            break
        except:
            print("Failed to create final image for pack " + (str(pack_id)) + "\nThis is attempt " + str(attempts))
            attempts = attempts + 1
    if final_image_file_name == "":
        response = await send_message_to_channel(user, content=final_content + "\n\nFailed to generate image file, please lookup cards.  Here are the card_img links:\n" + card_img_urls)
    else:
        to_send_file = discord.File("./" + final_image_file_name, final_image_file_name)
        response = await send_message_to_channel(user, content=final_content, file=to_send_file)
    x = 0
    for card in cards:
        await response.add_reaction(num_to_emoji[x+1])
        reaction_handler[num_to_emoji[x+1]] = [react_add_card_to_cardpool, [card.pack_card_id, card.pack_id]]
        x=x+1
    awaiting_reaction[response] = reaction_handler
    if final_image_file_name != "":
        os.remove('./' + final_image_file_name)

async def send_current_pack_all_players(game_id):
    player_ids = get_player_ids(game_id)
    for player_id in player_ids:
        player = await client.fetch_user(player_id)
        await clean_dms_for_player(player)
        await send_current_pack(game_id, player)

async def notify_of_game_end(game_id):
    player_ids = get_player_ids(game_id)
    for player_id in player_ids:
        player = await client.fetch_user(player_id)
        await send_message_to_channel(player,content=("Game " + str(game_id) + " complete.  All packs have been depleted. Send '$print_card_pool DCG " + str(game_id) + "' to see your final card pool"))

async def clean_dms_for_player(user):
    global messages_queued_for_deletion
    old_queue = messages_queued_for_deletion
    messages = await user.dm_channel.history().flatten()
    messages_queued_for_deletion = old_queue + messages
    for msg in messages:
        if msg not in old_queue:
            if isinstance(msg.channel,discord.channel.DMChannel) and msg.author == client.user:
                await msg.delete()
            elif (not isinstance(msg.channel,discord.channel.DMChannel)):
                await msg.delete()

async def react_clean_dms_for_player(reaction, user):
    global messages_queued_for_deletion
    old_queue = messages_queued_for_deletion
    messages = await user.dm_channel.history().flatten()
    messages_queued_for_deletion = old_queue + messages
    for msg in messages:
        if msg not in old_queue:
            if isinstance(msg.channel,discord.channel.DMChannel) and msg.author == client.user:
                await msg.delete()
            elif (not isinstance(msg.channel,discord.channel.DMChannel)):
                await msg.delete()

async def react_clean_all(reaction, user):
    global messages_queued_for_deletion
    old_queue = messages_queued_for_deletion
    message = reaction.message
    messages = await message.channel.history().flatten()
    messages_queued_for_deletion = old_queue + messages
    messages_to_delete = []
    for msg in messages:
        if len(messages_to_delete) < 100:
            if msg not in old_queue:
                if isinstance(msg.channel,discord.channel.DMChannel) and msg.author == client.user:
                    messages_to_delete.append(msg)
                elif (not isinstance(msg.channel,discord.channel.DMChannel)):
                    messages_to_delete.append(msg)
    await reaction.message.channel.delete_messages(messages_to_delete)

async def react_delete_message(reaction, user):
    message = reaction.message
    if isinstance(message.channel,discord.channel.DMChannel) and message.author == client.user:
        await message.delete()
    elif (not isinstance(message.channel,discord.channel.DMChannel)):
        await message.delete()

async def react_add_player_to_game(reaction, user):
    player_id = user.id
    game_id = game_start_message_to_game_id[reaction.message]
    seat_number = emoji_to_num[reaction.emoji]
    response = add_player_to_game(player_id, game_id, seat_number)
    await send_message_to_channel(reaction.message.channel,content=(response),delete_after=3)

async def react_kick_off_game(reaction, user):
    game_id = game_start_message_to_game_id[reaction.message]
    game = game_id_to_game_set_packs[game_id][0]
    set = game_id_to_game_set_packs[game_id][1]
    packs = int(game_id_to_game_set_packs[game_id][2])
    if not open_for_players(game_id):
        await send_message_to_channel(reaction.message.channel,content=("Game " + str(game_id) + " already kicked off!"),delete_after=3)
    else:
        if get_number_of_players(game_id) <= 1:
            await send_message_to_channel(reaction.message.channel,content=("You cannot start a game with one or fewer players!"""),delete_after=3)
        else:
            sql_stmt = """update games set open_for_players = 'N', goal_pick_num = 1 where game_id = """ + str(game_id) + """;"""
            run_sql(sql_stmt)
            con.commit()
            player_ids = get_player_ids(game_id)
            await send_message_to_channel(reaction.message.channel,content=("Generating packs..."),delete_after=3)
            for player_id in player_ids:
                for y in range(packs):
                    pack_id = generate_pack(game, set)
                    insert_into_game_packs_lkp(game_id, pack_id)
            for player_id in player_ids:
                pack_id = choose_unopened_pack(game_id)
                assign_pack_id_to_player(game_id, player_id, pack_id)
                player = await client.fetch_user(player_id)
                await send_current_pack(game_id, player)
            await send_message_to_channel(reaction.message.channel,content=("Kicking off game " + str(game_id) + "!"),delete_after=3)

async def react_add_card_to_cardpool(reaction, user, args):
    pack_card_id = args[0]
    pack_id = args[1]
    player_id = user.id
    game_id = get_game_id_by_pack_id(pack_id)
    if player_can_draft_card(game_id,player_id):
        if player_assigned_pack(player_id, pack_id, game_id):
            if not card_taken(pack_id, pack_card_id):
                increment_player_pick_num(player_id, game_id)
                add_card_to_cardpool(pack_card_id,pack_id,game_id,player_id)
                set_pack_card_to_taken(pack_id, pack_card_id)
                if time_to_continue(game_id):
                    if assigned_packs_depleted(game_id):
                        if all_packs_depleted(game_id):
                            await notify_of_game_end(game_id)
                        else:
                            get_next_rotation_direction(game_id)
                            assign_players_unopened_packs(game_id)
                            increment_player_goal_pick_num_all_players(game_id)
                            await send_current_pack_all_players(game_id)
                    else:
                        rotate_assigned_packs(game_id)
                        increment_player_goal_pick_num_all_players(game_id)
                        await send_current_pack_all_players(game_id)

async def send_message_to_channel(channel, content=None, tts=False, embed=None, file=None, files=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None):
    if channel in whitelisted_channels or isinstance(channel, discord.Member) or isinstance(channel, discord.User):
        sent_message = await channel.send(content=content, tts=tts, embed=embed, file=file, files=files, delete_after=delete_after, nonce=nonce, allowed_mentions=allowed_mentions, reference=reference, mention_author=mention_author)
        return sent_message
    else:
        print("Attempted to send message to non-whitelisted channel, returning NONE!")
        return None


################    EVENTS    ################

#Run When Connected to a Server (Guild)
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        print(str(client.user) + " is connected to " + str(guild.name) + " (id: " + str(guild.id) + ")")
        print("Members Currently Connected to " + str(guild.name) + ": ")
        for member in guild.members:
            print(member.name)
    load_whitelisted_channels_from_db()

#Run When a Member Sends a Message to a Connected Server (Guild)
@client.event
async def on_message(message):
    if message.author == client.user: #or isinstance(message.channel, discord.channel.DMChannel) or isinstance(message.channel, discord.channel.GroupChannel):
        return
    elif message.channel in whitelisted_channels or isinstance(message.channel, discord.channel.DMChannel) or message.content.startswith("$add_channel_to_whitelist"):
        if message.content.startswith("$"):
            if verbose == True:
                print(message.content)
            input = message.content.split(" ")
            await commands[input[0]](message)

#Run When a Member Reacts to a Message on a Connected Server (Guild)
@client.event
async def on_reaction_add(reaction, user):
    if user != client.user:
        if reaction.message in awaiting_reaction:
            if reaction.emoji in awaiting_reaction[reaction.message]:
                if isinstance(awaiting_reaction[reaction.message][reaction.emoji], list):
                    function = awaiting_reaction[reaction.message][reaction.emoji][0]
                    args = awaiting_reaction[reaction.message][reaction.emoji][1]
                    await function(reaction, user, args)
                else:
                    await awaiting_reaction[reaction.message][reaction.emoji](reaction, user)

################    MEMBER FUNCTIONS    ################
async def mf_ping(message):
    await send_message_to_channel(message.channel,content=reference_user(message.author) + " called the PING command",delete_after=3)
    await send_message_to_channel(message.channel,content="PONG",delete_after=3)

async def mf_add(message):
    input = message.content.split(" ")
    input.pop(0)
    total = 0
    for argument in input:
        total = total + int(argument)
    await send_message_to_channel(message.channel,content=(str(total)),delete_after=3)

async def mf_clean(message):
    await clean(message.channel)

async def mf_create_pack(message):
    input = message.content.split(" ")
    input.pop(0)
    generate_pack(input[0], input[1])

async def mf_show_pack(message):
    input = message.content.split(" ")
    input.pop(0)
    cards = get_cards(input[0])
    for card in cards:
        await send_message_to_channel(message.author,content=(card))

async def mf_reveal_pack(message):
    input = message.content.split(" ")
    input.pop(0)
    cards = get_cards(input[0])
    for card in cards:
        await send_message_to_channel(message.channel,content=(card))

async def mf_clean_all(message):
    response = await send_message_to_channel(message.channel,content=(reference_user(message.author) + " called the clean all command.\nThis will erase all message in this channel, regardless of their relevance to this bot.\nAre you sure you wish to continue?\nReact with 1️⃣ for 'Yes', 2️⃣  for 'No'"))
    await response.add_reaction("1️⃣")
    await response.add_reaction("2️⃣")
    reaction_handler = {
        "1️⃣": react_clean_all,
        "2️⃣": react_delete_message}
    awaiting_reaction[response] = reaction_handler

async def mf_clean_all_dm(message):
    response = await send_message_to_channel(message.author,content=(reference_user(message.author) + " called the clean all command.\nThis will erase all message in this channel, regardless of their relevance to this bot.\nAre you sure you wish to continue?\nReact with 1️⃣ for 'Yes', 2️⃣  for 'No'"))
    await response.add_reaction("1️⃣")
    await response.add_reaction("2️⃣")
    reaction_handler = {
        "1️⃣": react_clean_dms_for_player,
        "2️⃣": react_delete_message}
    awaiting_reaction[response] = reaction_handler

async def mf_start_game_draft(message):
    input = message.content.split(" ")
    input.pop(0)
    game = input[0]
    set = input[1]
    packs = input[2]
    response = await send_message_to_channel(message.channel,content=
        reference_user(message.author) + " has requested to start a draft game!\nPlease react with the number of the seat you would like!\nReact with ▶️ when you are ready to kick off!"
        , embed=discord.Embed().set_image(url=start_game_image))
    game_id = get_next_game_id()
    await response.add_reaction("1️⃣")
    await response.add_reaction("2️⃣")
    await response.add_reaction("3️⃣")
    await response.add_reaction("4️⃣")
    await response.add_reaction("5️⃣")
    await response.add_reaction("6️⃣")
    await response.add_reaction("7️⃣")
    await response.add_reaction("8️⃣")
    await response.add_reaction("▶️")
    reaction_handler = {
        "1️⃣": react_add_player_to_game
        ,"2️⃣": react_add_player_to_game
        ,"3️⃣": react_add_player_to_game
        ,"4️⃣": react_add_player_to_game
        ,"5️⃣": react_add_player_to_game
        ,"6️⃣": react_add_player_to_game
        ,"7️⃣": react_add_player_to_game
        ,"8️⃣": react_add_player_to_game
        ,"▶️": react_kick_off_game
        }
    awaiting_reaction[response] = reaction_handler
    game_start_message_to_game_id[response] = game_id
    game_id_to_game_set_packs[game_id] = [game, set, packs]

async def mf_print_card_pool(message):
    input = message.content.split(" ")
    input.pop(0)
    game = input[0]
    game_id = input[1]
    player_id = message.author.id
    card_pool = get_card_pool(game_id, player_id, game)
    file_name = write_card_pool_to_file(card_pool, game_id, message.author.id)
    to_send_file = discord.File("./" + file_name, file_name)
    await send_message_to_channel(message.author, content = reference_user(message.author) + "'s Card Pool for Game " + str(game_id), file=to_send_file)
    os.remove("./" + file_name)

async def mf_add_channel_to_whitelist(message):
    global whitelisted_channels
    if message.channel not in whitelisted_channels:
        whitelisted_channels.append(message.channel)
        add_channel_to_whitelist_in_db(message.channel)
        await send_message_to_channel(message.channel,content=("Channel " + str(message.channel) + " added to whitelist!"),delete_after=3)
    else:
        await send_message_to_channel(message.channel,content="Channel " + str(message.channel) + " already in whitelist!", delete_after=3)

async def mf_remove_channel_from_whitelist(message):
    global whitelisted_channels
    if message.channel in whitelisted_channels:
        await send_message_to_channel(message.channel, content = "Removing " + str(message.channel) + " from whitelist...", delete_after = 3)
        whitelisted_channels.remove(message.channel)
        remove_channel_from_whitelist_in_db(message.channel)

async def mf_start_game_sealed(message):
    input = message.content.split(" ")
    input.pop(0)
    game = input[0]
    set = input[1]
    packs = input[2]
    await send_message_to_channel(message.channel, content = "Generating " + reference_user(message.author) + "'s sealed pool...", delete_after = 10)
    game_id = get_next_game_id()
    add_player_to_game(message.author.id, game_id, 1)
    for x in range(int(packs)):
        pack_id = generate_pack(game, set)
        cards = get_cards(pack_id)
        for card in cards:
            add_card_to_cardpool(card.pack_card_id, card.pack_id, game_id, message.author.id)
    card_pool = get_card_pool(game_id, message.author.id, game)
    file_name = write_card_pool_to_file(card_pool, game_id, message.author.id)
    to_send_file = discord.File("./" + file_name, file_name)
    await send_message_to_channel(message.author, content = reference_user(message.author) + "'s Card Pool for Game " + str(game_id), file=to_send_file)


################    FUNCTION LIBRARY    ################
commands = {
"$ping": mf_ping
,"$add": mf_add
,"$clean": mf_clean
,"$create_pack": mf_create_pack
,"$show_pack": mf_show_pack
,"$reveal_pack": mf_reveal_pack
,"$clean_all": mf_clean_all
,"$start_game_draft": mf_start_game_draft
,"$print_card_pool": mf_print_card_pool
,"$add_channel_to_whitelist": mf_add_channel_to_whitelist
,"$remove_channel_from_whitelist": mf_remove_channel_from_whitelist
,"$clean_all_dm": mf_clean_all_dm
,"$start_game_sealed": mf_start_game_sealed
}





client.run(TOKEN)