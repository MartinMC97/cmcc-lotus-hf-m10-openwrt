ENTRY(_start)

PHDRS
{
	text PT_LOAD FILEHDR PHDRS FLAGS(5);
}

SECTIONS
{
	. = 0x10000 + SIZEOF_HEADERS;
	.text : { *(.text*) *(.rodata*) } :text
	/DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
