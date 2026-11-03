`timescale 1ns / 1ps

module tb_arrays;
    logic [7:0] a [0:2];
    logic [7:0] k;
    wire  [7:0] y [0:2];
    wire  [7:0] s;
    vec_pair dut (.*);
endmodule

// One element of a TB array on a plain port.
module tb_pick;
    logic [7:0] arr [0:2];
    logic [7:0] o;
    inc8 u (.a(arr[1]), .y(o));
endmodule
