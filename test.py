player_moves_1 = [(12,28),(28,35),(1,18),(6,12),(11,27)]
excepted_ai_moves_1 = [(51,35),(59,35),(35,36),(57,42),(36,45)]

player_moves_2 = [(12,28),(28,35),(1,18),(6,12),(11,27),(14,22),(5,14),(3,12),(12,19),(4,6)]
excepted_ai_moves_2 = [(51,35),(59,35),(35,36),(57,42),(36,45),(58,30),(30,12),(42,27),(60,58),(52,36)]

player_moves_3 = [(12,28),(28,35),(1,18),(6,12),(11,27),(14,22),(5,14),(3,12),(12,19),(4,6),(5,4),(18,28),(8,16),(9,25),(19,28),(2,20),(28,35),(35,36),(20,27),(36,4),(4,1),(14,23),(10,18),(23,37),(1,37),(37,55),(6,14),(14,23),(23,14),(14,6),(6,14),(14,7),(22,30)]
excepted_ai_moves_3 = [(51,35),(59,35),(35,36),(57,42),(36,45),(58,30),(30,12),(42,27),(60,58),(52,36),(61,34),(45,41),(62,45),(45,28),(34,43),(53,37),(43,25),(25,4),(41,27),(63,60),(49,41),(54,46),(27,18),(46,37),(58,57),(18,0),(0,16),(60,63),(63,55),(16,34),(59,11),(34,13),(11,3)]

class AIGenerationTest():
    def __init__(self, player_moves, excepted_ai_moves):
        self.manual_moves = player_moves
        self.expected_moves = excepted_ai_moves
        self.count = 0

    def get_manuel_move(self):
        if self.count > (len(self.manual_moves) - 1):
            return None
        return self.manual_moves[self.count]
    
    def is_expected_move(self, move):
        if move != self.expected_moves[self.count]:
            return False
        return True
    
    def inc_count(self):
        self.count += 1
