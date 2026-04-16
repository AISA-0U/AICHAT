def fibonacci(n):
    if n <= 0:
        return []
    if n == 1:
        return [0]
    if n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

result = fibonacci(20)
print("Fibonacci sequence first 20 terms:")
for i in range(len(result)):
    print("F(%d) = %d" % (i+1, result[i]))

print("\nTotal: %d terms" % len(result))