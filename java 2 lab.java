class Triangle {
    private int breadth;
    private int height;
    public Triangle() {
        this(0, 0);
    }
    public Triangle(int breadth, int height) {
        this.breadth = breadth;
        this.height = height;
    }
    public double calculateArea() {
        return 0.5 * breadth * height;
    }
    public static void main(String[] args) {
        Triangle t1 = new Triangle(10, 5);
        System.out.println("Area of triangle: " + t1.calculateArea());
    }
}






















