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
        if color == "white":
            self.number = 6
        else:
            self.number = -6

class Queen(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Queen"
        self.moves = [-7, 7, -9, 9, -1, 1, -8, 8]
        self.value = 900
        if color == "white":
            self.number = 5
        else:
            self.number = -5

class Bishop(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Bishop"
        self.moves = [-7, 7, -9, 9]
        self.value = 300
        if color == "white":
            self.number = 4
        else:
            self.number = -4

class Knight(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Knight"
        self.moves = [-17, -15, -10, -6, 6, 10, 15, 17]
        self.value = 300
        if color == "white":
            self.number = 3
        else:
            self.number = -3

class Rook(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Rook"
        self.moves = [-1, 1, -8, 8]
        self.value = 500
        self.not_moved = True
        if color == "white":
            self.number = 2
        else:
            self.number = -2

class Pawn(ChessPiece):
    def __init__(self, color):
        super().__init__(color)
        self.name = "Pawn"
        self.value = 100
        self.not_moved = True
        if self.color == "white":
            self.move = 8
            self.attack_moves = [7, 9]
            self.number = 1
        else:
            self.move = -8
            self.attack_moves = [-7, -9]
            self.number = -1