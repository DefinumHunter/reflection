// Array-port fixtures for the netlist/model engine. Not part of the accelerator.
// No `timescale here on purpose: arrays_tb.sv has one, so the default must apply.

module vadd3 (input logic [7:0] a [0:2], input logic [7:0] k, output logic [7:0] y [0:2]);
    always_comb for (int i = 0; i < 3; i++) y[i] = a[i] + k + 8'(i);
endmodule

module sum3 (input logic [7:0] v [0:2], output logic [7:0] s);
    assign s = v[0] + v[1] + v[2];
endmodule

// Structure only. m is declared [2:0], the ports [0:2]: arrays connect by
// position, so port element 0 is m[2].
module vec_pair (input logic [7:0] a [0:2], input logic [7:0] k,
                 output logic [7:0] y [0:2], output logic [7:0] s);
    logic [7:0] m [2:0];
    vadd3 u1 (.a(a), .k(k), .y(m));
    vadd3 u2 (.a(m), .k(k), .y(y));
    sum3  u3 (.v(y), .s(s));
endmodule
