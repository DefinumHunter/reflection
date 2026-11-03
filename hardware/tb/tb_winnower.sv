`timescale 1ns/1ps

module tb_winnower;
    localparam int NUM_SLOTS = 9;
    localparam int GROUPS = 3;

    logic clk, rst_n;

    logic [NUM_SLOTS*32-1:0] win_data_packed;
    logic [NUM_SLOTS*4-1:0]  win_id_packed;
    logic [NUM_SLOTS-1:0]    win_valid_packed;
    logic [GROUPS*32-1:0]    cordic_data_packed;
    logic [GROUPS*4-1:0]     cordic_id_packed;
    logic [GROUPS-1:0]       cordic_valid_packed;

    logic [NUM_SLOTS*32-1:0] out_data_packed;
    logic [NUM_SLOTS*4-1:0]  out_id_packed;
    logic [31:0] crc32;
    logic        out_valid;

    logic signed [31:0] win_data  [0:NUM_SLOTS-1];
    logic         [3:0] win_id    [0:NUM_SLOTS-1];
    logic               win_valid [0:NUM_SLOTS-1];
    logic signed [31:0] cordic_data  [0:GROUPS-1];
    logic         [3:0] cordic_id    [0:GROUPS-1];
    logic               cordic_valid [0:GROUPS-1];

    genvar i;
    generate
        for (i = 0; i < NUM_SLOTS; i++) begin : pack_in
            assign win_data[i]  = win_data_packed[i*32 +: 32];
            assign win_id[i]    = win_id_packed[i*4 +: 4];
            assign win_valid[i] = win_valid_packed[i];
        end
        for (i = 0; i < GROUPS; i++) begin : pack_cordic_in
            assign cordic_data[i]  = cordic_data_packed[i*32 +: 32];
            assign cordic_id[i]    = cordic_id_packed[i*4 +: 4];
            assign cordic_valid[i] = cordic_valid_packed[i];
        end
        // outputs: hierarchical reference, NOT the port connection (confirmed
        // broken for unpacked-array output ports on this Icarus version)
        for (i = 0; i < NUM_SLOTS; i++) begin : pack_out
            assign out_data_packed[i*32 +: 32] = dut.out_data[i];
            assign out_id_packed[i*4 +: 4]     = dut.out_id[i];
        end
    endgenerate

    winnower dut (
        .clk(clk),
        .rst_n(rst_n),
        .win_data(win_data),
        .win_id(win_id),
        .win_valid(win_valid),
        .cordic_data(cordic_data),
        .cordic_id(cordic_id),
        .cordic_valid(cordic_valid),
        .crc32(crc32),
        .out_valid(out_valid)
        // out_data/out_id left unconnected — read via hierarchy above
    );

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_winnower);
    end
endmodule
