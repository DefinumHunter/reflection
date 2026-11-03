`timescale 1ns/1ps

module tb_array_output_router;
    localparam int NUM_SLOTS = 9;
    localparam int GROUPS = 3;
    localparam int SLOTS_PER_GROUP = 3;

    logic clk;
    logic rst_n;

    // ---- Packed scalar boundary for cocotb (VPI-friendly) ----
    logic [NUM_SLOTS*32-1:0] slot_data_packed;
    logic [NUM_SLOTS*4-1:0]  slot_id_packed;
    logic [NUM_SLOTS-1:0]    slot_valid_packed;
    logic [GROUPS*2-1:0]     route_mode_packed;

    logic [NUM_SLOTS*32-1:0] win_data_packed;
    logic [NUM_SLOTS*4-1:0]  win_id_packed;
    logic [NUM_SLOTS-1:0]    win_valid_packed;

    logic [NUM_SLOTS*32-1:0] tempbuf_data_packed;
    logic [NUM_SLOTS*4-1:0]  tempbuf_id_packed;
    logic [NUM_SLOTS-1:0]    tempbuf_valid_packed;

    logic [GROUPS*32-1:0] cordic_data_packed;
    logic [GROUPS*4-1:0]  cordic_id_packed;
    logic [GROUPS-1:0]    cordic_valid_packed;

    // ---- Unpacked-array signals for the DUT's INPUT ports only.
    // (Input array-port connections DO propagate correctly through Icarus;
    // it's specifically OUTPUT array ports that don't — see below.) ----
    logic signed [31:0] slot_data  [0:NUM_SLOTS-1];
    logic         [3:0] slot_id    [0:NUM_SLOTS-1];
    logic               slot_valid [0:NUM_SLOTS-1];
    logic         [1:0] route_mode [0:GROUPS-1];

    genvar i, g;
    generate
        for (i = 0; i < NUM_SLOTS; i++) begin : pack_in
            assign slot_data[i]  = slot_data_packed[i*32 +: 32];
            assign slot_id[i]    = slot_id_packed[i*4 +: 4];
            assign slot_valid[i] = slot_valid_packed[i];
        end
        for (g = 0; g < GROUPS; g++) begin : pack_mode
            assign route_mode[g] = route_mode_packed[g*2 +: 2];
        end
        // OUTPUTS: read via HIERARCHICAL REFERENCE into the dut instance,
        // not through the port connection — Icarus does not propagate
        // unpacked-array OUTPUT port connections in this version, confirmed
        // by direct reproduction (input side works, output side doesn't).
        for (i = 0; i < NUM_SLOTS; i++) begin : pack_out
            assign win_data_packed[i*32 +: 32]     = dut.win_data[i];
            assign win_id_packed[i*4 +: 4]         = dut.win_id[i];
            assign win_valid_packed[i]             = dut.win_valid[i];
            assign tempbuf_data_packed[i*32 +: 32] = dut.tempbuf_data[i];
            assign tempbuf_id_packed[i*4 +: 4]     = dut.tempbuf_id[i];
            assign tempbuf_valid_packed[i]         = dut.tempbuf_valid[i];
        end
        for (g = 0; g < GROUPS; g++) begin : pack_cordic
            assign cordic_data_packed[g*32 +: 32] = dut.cordic_data[g];
            assign cordic_id_packed[g*4 +: 4]     = dut.cordic_id[g];
            assign cordic_valid_packed[g]         = dut.cordic_valid[g];
        end
    endgenerate

    array_output_router dut (
        .clk(clk),
        .rst_n(rst_n),
        .slot_data(slot_data),
        .slot_id(slot_id),
        .slot_valid(slot_valid),
        .route_mode(route_mode)
        // output ports intentionally left unconnected — read via hierarchy above
    );

    array_output_router_sva_icarus u_sva (
        .clk(clk),
        .rst_n(rst_n)
    );

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_array_output_router);
    end
endmodule
