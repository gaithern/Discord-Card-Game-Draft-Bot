class Card:
    name = ""
    set_acro_plus_number = ""
    pack_id = 0
    pack_card_id = 0
    card_img_url = ""
    
    def __init__(self, name, set_acro_plus_number, pack_id, pack_card_id, card_img_url):
        self.name = name
        self.set_acro_plus_number = set_acro_plus_number
        self.pack_id = pack_id
        self.pack_card_id = pack_card_id
        self.card_img_url = card_img_url
    
    def __str__(self):
        return "pack_id=" + str(self.pack_id) + "\npack_card_id=" + str(self.pack_card_id)