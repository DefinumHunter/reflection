module array_output_router #(
    parameter int NUM_SLOTS       = 9,
    parameter int GROUPS          = 3,
    parameter int SLOTS_PER_GROUP = 3
)(
    input  logic clk,
    input  logic rst_n,

    // От каждого из 9 pe_output_strapping (сторона out_valid_final)
    input  logic signed [31:0] slot_data  [0:NUM_SLOTS-1],
    input  logic         [3:0] slot_id    [0:NUM_SLOTS-1],
    input  logic               slot_valid [0:NUM_SLOTS-1],  // импульс, 1 такт

    // Persistent-конфиг маршрута на группу (меняется редко, по глобальной команде)
    //   2'b00 = Winnower       (непрерывное чтение, без захвата)
    //   2'b01 = CORDIC         (round-robin, с захватом и гашением valid)
    //   2'b10 = temp_buf       (непрерывное чтение, без захвата — как Winnower)
    input  logic [1:0] route_mode [0:GROUPS-1],

    // ---- Непрерывный путь: Winnower ----
    output logic signed [31:0] win_data  [0:NUM_SLOTS-1],
    output logic         [3:0] win_id    [0:NUM_SLOTS-1],
    output logic               win_valid [0:NUM_SLOTS-1],

    // ---- Непрерывный путь: temp_buf (для переиспользуемых констант — например,
    //      глобальный коэффициент, который потом много раз подаётся обратно
    //      во вход массива через pe_input_mux.buf_wr, вне этого модуля) ----
    output logic signed [31:0] tempbuf_data  [0:NUM_SLOTS-1],
    output logic         [3:0] tempbuf_id    [0:NUM_SLOTS-1],
    output logic               tempbuf_valid [0:NUM_SLOTS-1],

    // ---- Путь на CORDIC: один интерфейс на группу/CORDIC ----
    output logic signed [31:0] cordic_data  [0:GROUPS-1],
    output logic         [3:0] cordic_id    [0:GROUPS-1],
    output logic               cordic_valid [0:GROUPS-1]
);

    localparam logic [1:0] ROUTE_WINNOWER = 2'b00;
    localparam logic [1:0] ROUTE_CORDIC   = 2'b01;
    localparam logic [1:0] ROUTE_TEMPBUF  = 2'b10;

    // --- Захват для CORDIC-пути: одноимпульсный slot_valid иначе потеряется,
    //     пока round-robin счётчик до него не дойдёт ---
    logic signed [31:0] pend_data  [0:NUM_SLOTS-1];
    logic         [3:0] pend_id    [0:NUM_SLOTS-1];
    logic               pend_valid [0:NUM_SLOTS-1];

    // --- Round-robin счётчик на каждую группу (0,1,2,0,1,2...) ---
    logic [1:0] rr_cnt [0:GROUPS-1];

    genvar g, s;
    generate
        for (g = 0; g < GROUPS; g++) begin : route_group

            // ---------------- Непрерывный путь: Winnower ----------------
            for (s = 0; s < SLOTS_PER_GROUP; s++) begin : winnower_path
                localparam int SLOT = g*SLOTS_PER_GROUP + s;

                assign win_data[SLOT]  = slot_data[SLOT];
                // Гейтим id тем же условием, что и valid — сентинел id=0000
                // должен быть надёжен уже на выходе роутера, а не только выше по потоку.
                assign win_id[SLOT]    = ((route_mode[g] == ROUTE_WINNOWER) & slot_valid[SLOT])
                                        ? slot_id[SLOT] : 4'b0000;
                assign win_valid[SLOT] = (route_mode[g] == ROUTE_WINNOWER) & slot_valid[SLOT];
            end

            // ---------------- Непрерывный путь: temp_buf ----------------
            for (s = 0; s < SLOTS_PER_GROUP; s++) begin : tempbuf_path
                localparam int SLOT = g*SLOTS_PER_GROUP + s;

                assign tempbuf_data[SLOT]  = slot_data[SLOT];
                assign tempbuf_id[SLOT]    = ((route_mode[g] == ROUTE_TEMPBUF) & slot_valid[SLOT])
                                            ? slot_id[SLOT] : 4'b0000;
                assign tempbuf_valid[SLOT] = (route_mode[g] == ROUTE_TEMPBUF) & slot_valid[SLOT];
            end

            // ---------------- Захват + round-robin (CORDIC-путь) ----------------
            for (s = 0; s < SLOTS_PER_GROUP; s++) begin : cordic_capture
                localparam int SLOT = g*SLOTS_PER_GROUP + s;

                always_ff @(posedge clk) begin
                    if (!rst_n) begin
                        pend_data[SLOT]  <= '0;
                        pend_id[SLOT]    <= '0;
                        pend_valid[SLOT] <= 1'b0;
                    end else if (slot_valid[SLOT]) begin
                        pend_data[SLOT]  <= slot_data[SLOT];
                        pend_id[SLOT]    <= slot_id[SLOT];
                        pend_valid[SLOT] <= 1'b1;
                    end else if (rr_cnt[g] == s[1:0] && route_mode[g] == ROUTE_CORDIC) begin
                        pend_valid[SLOT] <= 1'b0;
                    end
                end
            end

            // ---------------- Счётчик очереди группы ----------------
            always_ff @(posedge clk) begin
                if (!rst_n) begin
                    rr_cnt[g] <= 2'd0;
                end else if (route_mode[g] == ROUTE_CORDIC) begin
                    rr_cnt[g] <= (rr_cnt[g] == 2'd2) ? 2'd0 : rr_cnt[g] + 2'd1;
                end
            end

            // ---------------- Выход к своему CORDIC ----------------
            logic signed [31:0] mux_data;
            logic         [3:0] mux_id;
            logic               mux_valid;

            assign mux_data  = ({32{rr_cnt[g] == 2'd0}} & pend_data[g*SLOTS_PER_GROUP+0])
                              | ({32{rr_cnt[g] == 2'd1}} & pend_data[g*SLOTS_PER_GROUP+1])
                              | ({32{rr_cnt[g] == 2'd2}} & pend_data[g*SLOTS_PER_GROUP+2]);
            assign mux_id    = ({4{rr_cnt[g] == 2'd0}} & pend_id[g*SLOTS_PER_GROUP+0])
                              | ({4{rr_cnt[g] == 2'd1}} & pend_id[g*SLOTS_PER_GROUP+1])
                              | ({4{rr_cnt[g] == 2'd2}} & pend_id[g*SLOTS_PER_GROUP+2]);
            assign mux_valid = (rr_cnt[g] == 2'd0 && pend_valid[g*SLOTS_PER_GROUP+0])
                             | (rr_cnt[g] == 2'd1 && pend_valid[g*SLOTS_PER_GROUP+1])
                             | (rr_cnt[g] == 2'd2 && pend_valid[g*SLOTS_PER_GROUP+2]);

            assign cordic_data[g]  = (route_mode[g] == ROUTE_CORDIC) ? mux_data  : '0;
            assign cordic_id[g]    = (route_mode[g] == ROUTE_CORDIC) ? mux_id    : '0;
            assign cordic_valid[g] = (route_mode[g] == ROUTE_CORDIC) ? mux_valid : 1'b0;

        end
    endgenerate

endmodule
