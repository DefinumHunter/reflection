// Worked example for array ports: three registered lanes and their sum.
module vec_reg (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] a [0:2],
    input  logic [7:0] k,
    output logic [7:0] y [0:2],
    output logic [7:0] s
);
    always_ff @(posedge clk)
        for (int i = 0; i < 3; i++)
            y[i] <= !rst_n ? 8'd0 : a[i] + k + 8'(i);
    assign s = y[0] + y[1] + y[2];
endmodule
