# =============================================================================
# Makefile – baut das Pruefstand-Programm
# =============================================================================
#   make          baut ./pruefstand
#   make run      baut und startet (http://localhost:8080)
#   make clean    loescht build/ und ./pruefstand

CXX ?= g++
CC  ?= gcc

# Einstellungen fuer Mongoose (lib/mongoose):
#   MG_TLS=MG_TLS_BUILTIN    HTTPS ohne OpenSSL (eingebautes TLS 1.3, braucht EC-Schluessel, siehe start.sh)
#   MG_MAX_RECV_SIZE         groesste Nachricht: ein Video-Teil vom Handy ist ca. 1 MB -> 16 MB Reserve
MONGOOSE = -DMG_TLS=MG_TLS_BUILTIN -DMG_MAX_RECV_SIZE=16777216

CXXFLAGS += -std=c++17 -O2 -Wall -Wextra -Isrc -Ilib/mongoose $(MONGOOSE)
CFLAGS   += -O2 -Ilib/mongoose $(MONGOOSE)

OBJ = build/main.o build/pruefstand.o build/messung.o build/webserver.o build/mongoose.o

pruefstand: $(OBJ)
	$(CXX) -o $@ $^

build/%.o: src/%.cpp src/*.hpp | build
	$(CXX) $(CXXFLAGS) -c -o $@ $<

build/mongoose.o: lib/mongoose/mongoose.c lib/mongoose/mongoose.h | build
	$(CC) $(CFLAGS) -c -o $@ $<

build:
	mkdir -p build

run: pruefstand
	./pruefstand

clean:
	rm -rf build pruefstand

.PHONY: run clean
