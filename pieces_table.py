pawn_table = [0,  0,  0,  0,  0,  0,  0,  0,
			100, 100, 100, 100, 100, 100, 100, 100,
			20, 20, 60, 70, 70, 60, 20, 20,
			5,  5, 50, 60, 60, 50,  5,  5,
			5,  0,  10, 55, 55,  10,  0,  5,
			5, 10, 10,  0,  0, 10, 10,  5,
			5,  -10, 0,-30,-30, 0, -10,  5,
			0,  0,  0,  0,  0,  0,  0,  0]


knight_table =   [-50,-40,-30,-30,-30,-30,-40,-50,
                -40,-20,  0,  0,  0,  0,-20,-40,
                -10,  0, 10, 15, 15, 10,  0,-10,
                -10,  5, 15, 20, 20, 15,  5,-10,
                -10,  0, 15, 20, 20, 15,  0,-10,
                -10,  5, 10, 15, 15, 10,  5,-10,
                -40,-20,  0,  5,  5,  0,-20,-40,
                -50,-40,-30,-30,-30,-30,-40,-50]


bishop_table =   [-20,-10,-10,-10,-10,-10,-10,-20,
                -10,  0,  0,  0,  0,  0,  0,-10,
                -10,  0,  5, 10, 10,  5,  0,-10,
                -10,  5,  5, 10, 10,  5,  5,-10,
                -10,  0, 10, 10, 10, 10,  0,-10,
                -10, 10, 10, 10, 10, 10, 10,-10,
                -10,  5,  0,  5,  5,  0,  5,-10,
                -20,-10,-30,-10,-10,-30,-10,-20,]

rook_table = [0,  0,  0,  0,  0,  0,  0,  0,
			5, 10, 10, 10, 10, 10, 10,  5,
			-5,  0,  0,  0,  0,  0,  0, -5,
			-5,  0,  0,  0,  0,  0,  0, -5,
			-5,  0,  0,  0,  0,  0,  0, -5,
			-5,  0,  0,  0,  0,  0,  0, -5,
			-5,  0,  0,  0,  0,  0,  0, -5,
			0,  0,  20,  20,  20,  20,  0,  0]

queen_table = [-20,-10,-10, -5, -5,-10,-10,-20,
			-10,  0,  0,  0,  0,  0,  0,-10,
			-10,  0,  5,  5,  5,  5,  0,-10,
			-5,  0,  5,  5,  5,  5,  0, -5,
			0,  0,  5,  5,  5,  5,  0, -5,
			-10,  5,  5,  5,  5,  5,  5,-10,
			-10,  0,  0,  0,  0,  0,  0,-10,
			-20,-10,-10, -5, -5,-10,-10,-20]

king_early_table =   [-30,-40,-40,-50,-50,-40,-40,-30,
                    -30,-40,-40,-50,-50,-40,-40,-30,
                    -30,-40,-40,-50,-50,-40,-40,-30,
                    -30,-40,-40,-50,-50,-40,-40,-30,
                    -20,-30,-30,-40,-40,-30,-30,-20,
                    -10,-20,-20,-20,-20,-20,-20,-10,
                    20, 20,  0,  0,  0,  0, 20, 20,
                    20, 30, 10,  5,  5, 5, 30, 20]

king_late_table = [-100,-50,-30,-20,-20,-30,-50,-100,
                -50,-30,-10,  0,  0,-10,-20,-50,
                -50,-30, 20, 30, 30, 20,-30,-50,
                -50,-30, 30, 40, 40, 30,-30,-50,
                -50,-30, 30, 40, 40, 30,-30,-50,
                -50,-30, 20, 30, 30, 20,-30,-50,
                -50,-30,-20,-20,-20,-20,-30,-50,
                -100,-50,-50,-50,-50,-50,-50,-100]