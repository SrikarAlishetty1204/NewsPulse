CREATE TABLE Categories (Id INT IDENTITY(1,1) PRIMARY KEY,Name VARCHAR(50) NOT NULL);

CREATE TABLE NewsArticles 
(
	Id INT IDENTITY(1,1) PRIMARY KEY,
	News VARCHAR(MAX) NOT NULL,
	Url VARCHAR(2048) NOT NULL,
	CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),
	CategoryId INT NOT NULL,
	Importance INT NOT NULL CHECK (Importance BETWEEN 1 AND 10),
	FOREIGN KEY (CategoryId) REFERENCES Categories(Id)
);

SELECT * FROM Categories;
SELECT * FROM NewsArticles;

INSERT INTO Categories (Name)
VALUES ('World'), ('India'), ('Technology'), ('Business'),
  ('Science'), ('Sports'), ('Health'), ('Other');