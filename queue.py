class Queue:
    def __init__(self):
        self.items = []
        
    def isEmpty(self):
        return len(self.items) == 0
    
    def insert(self, value):
        self.items.append(value)
        
    def remove(self):
        if self.isEmpty():
            return True
        return self.items.pop(0)
        
q = Queue()


q.insert(1)
q.insert(2)

print(q.remove())
print(q.remove())
print(q.isEmpty())  # Output: False

print(q.remove())  # Output: True