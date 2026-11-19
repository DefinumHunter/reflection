`timescale 1ns/1ps

interface data_if;
    logic [31:0] data;
    logic valid;
    modport source (output data, valid);
    modport sink (input data, valid);
endinterface
