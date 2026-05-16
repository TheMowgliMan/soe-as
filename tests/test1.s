# This is a comment

%macro test_macro
    add &r2, &r32
    movr &r32, &r2
%endmacro

%sect data
one:
    $1

%sect text
.next:
    test_macro
    jmp .next

# Entry point
main:
    movli one, &r2
    test_macro
    jmp .next
