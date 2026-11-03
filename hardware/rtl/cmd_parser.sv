module cmd_parser (
    input  logic       clk,
    input  logic       rst_n,

    input  logic       frame_vld,   // валид этого такта (уже без глобальных команд — они отфильтрованы выше)

    // Пока разбираем только первые 5 бит из 12. Остальное — резерв под CORDIC/нормализацию.
    //   cmd[4]   — ring/final    (независимый флаг, для pe_output_strapping)
    //   cmd[3:1] — preadder-опкод (PASS/direct/buf/sum+/sum-, для pe_input_mux)
    //   cmd[0]   — sub_post      (независимый флаг, для pe_output_strapping)
    input  logic [4:0] cmd,

    // ===================== -> pe_input_mux =====================
    output logic [1:0] sel,
    output logic       sub_pre,
    output logic       issue_vld,

    // ===================== -> pe_output_strapping ================
    output logic       ring_final,   // транзитом едет вместе с данными через mac_q16
    output logic       sub_post
);

    // Preadder-опкод — не набор независимых битов, а компактная команда
    localparam logic [2:0] OP_PASS   = 3'b000;
    localparam logic [2:0] OP_DIRECT = 3'b001;
    localparam logic [2:0] OP_BUF    = 3'b010;
    localparam logic [2:0] OP_SUM_P  = 3'b011;  // sum+
    localparam logic [2:0] OP_SUM_M  = 3'b100;  // sum-

    logic [2:0] preadder_op;
    assign preadder_op = cmd[3:1];

    // Единственный бит состояния: "предыдущий такт был sum+/sum-, сейчас ждём C"
    logic waiting_c;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            sel        <= 2'b00;
            sub_pre    <= 1'b0;
            issue_vld  <= 1'b0;
            ring_final <= 1'b0;
            sub_post   <= 1'b0;
            waiting_c  <= 1'b0;
        end else if (!frame_vld) begin
            issue_vld <= 1'b0;   // ничего не выдаём, состояние (waiting_c) не трогаем
        end else begin

            // ---------------- preadder / sel (-> pe_input_mux) ----------------
            if (waiting_c) begin
                // Ждали C — не разбираем сейчас preadder_op вообще, просто берём C
                sel       <= 2'b10;
                issue_vld <= 1'b1;
                waiting_c <= 1'b0;
            end else begin
                case (preadder_op)
                    OP_PASS: begin
                        sel       <= 2'b00;   // не важно, issue_vld=0
                        issue_vld <= 1'b0;
                    end
                    OP_DIRECT: begin
                        sel       <= 2'b00;
                        issue_vld <= 1'b1;
                    end
                    OP_BUF: begin
                        sel       <= 2'b11;
                        issue_vld <= 1'b1;
                    end
                    OP_SUM_P: begin
                        sel       <= 2'b01;
                        sub_pre   <= 1'b0;
                        issue_vld <= 1'b0;
                        waiting_c <= 1'b1;
                    end
                    OP_SUM_M: begin
                        sel       <= 2'b01;
                        sub_pre   <= 1'b1;
                        issue_vld <= 1'b0;
                        waiting_c <= 1'b1;
                    end
                    default: begin
                        sel       <= 2'b00;
                        issue_vld <= 1'b0;
                    end
                endcase
            end

            // ---------------- ring/final, sub_post (-> pe_output_strapping) ----
            // Независимые параллельные поля — просто транзит, каждый такт,
            // никак не завязаны на preadder/waiting_c
            ring_final <= cmd[4];
            sub_post   <= cmd[0];

        end
    end

endmodule
