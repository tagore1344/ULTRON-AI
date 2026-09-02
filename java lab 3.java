class ElectricityBill {
    private final int billId;
    private final String customerName;
    private final double meterReading;
    private double bill;
    // Constructor
    public ElectricityBill(int billId, String customerName, double meterReading) {
        this.billId = billId;
        this.customerName = customerName;
        this.meterReading = meterReading;
        this.bill = 0;
        calculateBill();
    }
    private void calculateBill() {
        if (this.meterReading < 20) {
            this.bill = this.bill + 100;
        } else if (this.meterReading < 50) {
            this.bill = this.bill + 200;
        } else {
            this.bill = this.bill + 500;
        }
    }
    public void displayDetails() {
        System.out.println("Bill Details: ");
        System.out.println("Bill ID: " + billId);
        System.out.println("Customer Name: " + customerName);
        System.out.println("Meter Reading: " + meterReading);
        System.out.println("Total Bill: " + bill + " Rs.");
    }
}
