class ChessPiece:
    def __init__(self, color):
        self.color = color
        

class King(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "King"
        self.moves = [-1, 1, -8 , 8, -7 , 7, -9, 9]
        self.value = 0
        self.not_moved = True

class Queen(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Queen"
        self.moves = [-7, 7, -9, 9, -1, 1, -8, 8]
        self.value = 900

class Bishop(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Bishop"
        self.moves = [-7, 7, -9, 9]
        self.value = 300

class Knight(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Knight"
        self.moves = [-17, -15, -10, -6, 6, 10, 15, 17]
        self.value = 300

class Rook(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Rook"
        self.moves = [-1, 1, -8, 8]
        self.value = 500
        self.not_moved = True

class Pawn(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Pawn"
        self.value = 100
        self.not_moved = True
        if self.color == "white":
            self.move = 8
            self.attack_moves = [7, 9]
        else:
            self.move = -8
            self.attack_moves = [-7, -9]