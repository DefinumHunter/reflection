// Small fixtures for the netlist/model engine. Not part of the accelerator.

module inc8 (input logic [7:0] a, output logic [7:0] y);
    assign y = a + 8'd1;
endmodule

module reg8 (input logic clk, input logic [7:0] d, output logic [7:0] q);
    always_ff @(posedge clk) q <= d;
endmodule

// Comb chain declared out of order: u2 reads what u1 drives, u1 is declared later.
module tb_chain;
    logic [7:0] x, m1, m2, y;
    inc8 u2 (.a(m1), .y(m2));
    inc8 u3 (.a(m2), .y(y));
    inc8 u1 (.a(x),  .y(m1));
endmodule

// Pure comb loop: must be reported, not hang.
module tb_loop;
    logic [7:0] a, b;
    inc8 u1 (.a(a), .y(b));
    inc8 u2 (.a(b), .y(a));
endmodule

// Loop broken by a register: a counter.
module tb_counter;
    logic clk;
    logic [7:0] q, d;
    inc8 u_inc (.a(q), .y(d));
    reg8 u_reg (.clk(clk), .d(d), .q(q));
endmodule

// Hierarchy with no component for the wrapper, assign aliases, generate chain.
module inc_pair (input logic [7:0] a, output logic [7:0] y);
    logic [7:0] mid;
    inc8 i0 (.a(a),   .y(mid));
    inc8 i1 (.a(mid), .y(y));
endmodule

module tb_hier #(parameter int N = 3);
    logic [7:0] x, y;
    logic [7:0] chain [0:N];
    assign chain[0] = x;
    for (genvar i = 0; i < N; i++) begin : g
        inc_pair p (.a(chain[i]), .y(chain[i+1]));
    end
    assign y = chain[N];
endmodule
