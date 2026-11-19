CXX      = g++
CXXFLAGS = -O2 -std=c++17 -Wall -Wextra -g
TARGET   = build/motor_tasten
SRC      = src/motor_tasten.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $^

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)

.PHONY: all run clean
