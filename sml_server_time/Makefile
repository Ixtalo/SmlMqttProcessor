UNAME := $(shell uname)
CFLAGS += -I./libsml/sml/include/ -g -std=c99 -Wall -Wextra -pedantic
OBJS = sml_server_time.o
LIBSML = ./libsml/sml/lib/libsml.a

LIBS = -lm
ifneq ($(UNAME), Darwin)
LIBS += -luuid
endif

all: sml_server_time

sml_server_time: $(OBJS) $(LIBSML)
	$(CC) $(OBJS) $(LIBSML) $(LIBS) -o sml_server_time

%.o: %.c
	$(CC) $(CFLAGS) -c $^ -o $@

.PHONY: clean install uninstall
clean:
	@rm -f *.o
	@rm -f sml_server_time
