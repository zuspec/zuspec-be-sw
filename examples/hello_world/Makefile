EXAMPLES_HELLO_WORLD_DIR:=$(dir $(abspath $(lastword $(MAKEFILE_LIST))))

all : hello_world.exe

CFLAGS += -I$(EXAMPLES_HELLO_WORLD_DIR)/../../runtime
CFLAGS += -g
#CFLAGS += -O3

hello_world.exe : hello_world.o zsp_rt_posix.o hello_world_main.o
	$(CC) $(CFLAGS) -o $@ $^

%.o : $(EXAMPLES_HELLO_WORLD_DIR)/../../runtime/%.c
	$(CC) -c $(CFLAGS) -o $@ $^

clean :
	rm -f *.o *.exe
