# This is a comment

%macro increment
    add &r32, &r32 # Equivalent to `&r32 = &r32 + &r2` because of the use of accumulator
%endmacro

%macro jmp_r4
    push &rac
    movll $1, &r2
    sub &r4, &r4 # Equivalent to `&r4 = &r4 - &r2` because of the use of accumulator
    pop &rac
    movr &r4, &rip
%endmacro

%sect text
%entry_point main:
    movll $1, &rac
    movll $0, &r32
    increment
    movll .next, &r4
    jmp_r4

.next:
    increment
    movll .next, &r4
    jmp_r4
