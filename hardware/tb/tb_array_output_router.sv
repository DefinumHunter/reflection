`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of array_output_router.
// No logic here: the bench drives and samples these signals.
// Port widths depend on parameters: they are for the default values.

module tb_array_output_router;
    parameter int NUM_SLOTS = 9;
    parameter int GROUPS = 3;
    parameter int SLOTS_PER_GROUP = 3;

    logic               clk;
    logic               rst_n;
    logic signed [31:0] slot_data [0:8];
    logic [3:0]         slot_id [0:8];
    logic               slot_valid [0:8];
    logic [1:0]         route_mode [0:2];
    wire  signed [31:0] win_data [0:8];
    wire  [3:0]         win_id [0:8];
    wire                win_valid [0:8];
    wire  signed [31:0] tempbuf_data [0:8];
    wire  [3:0]         tempbuf_id [0:8];
    wire                tempbuf_valid [0:8];
    wire  signed [31:0] cordic_data [0:2];
    wire  [3:0]         cordic_id [0:2];
    wire                cordic_valid [0:2];

    array_output_router #(.NUM_SLOTS(NUM_SLOTS), .GROUPS(GROUPS), .SLOTS_PER_GROUP(SLOTS_PER_GROUP)) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_array_output_router);
    end
endmodule
