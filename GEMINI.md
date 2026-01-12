# follow these principles

## KISS (Keep It Simple, Stupid)

- Encourages Gemini to write straightforward, uncomplicated solutions
- Avoids over-engineering and unnecessary complexity
- Results in more readable and maintainable code

## YAGNI (You Aren't Gonna Need It)

- Prevents Gemini from adding speculative features
- Focuses on implementing only what's currently needed
- Reduces code bloat and maintenance overhead

## SOLID Principles

- Single Responsibility Principle
- Open-Closed Principle
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

## Code Architecture

1. 对于Python、JavaScript、TypeScript 等动态语言,尽可能确保每个代码文件不要超过200行
2. 对于Java、Go、Rust 等静态语言,尽可能确保每个代码文件不要超过250行
3. 每层文件夹中的文件,尽可能不超过8个。如有超过,需要规划为多层子文件夹

- 除了硬性指标以外,还需要时刻关注优雅的架构设计,避免出现以下可能侵蚀我们代码质量的「坏味道」:

1. 僵化(Rigidity):系统难以变更,任何微小的改动都会引发一连串的连锁修改。
2. 冗余(Redundancy):同样的代码逻辑在多处重复出现, 导致维护困难且容易产生不一致。
3. 循环依赖(Circular Dependency):两个或多个模块互相纠缠,形成无法解耦的“死结”,导致难以测试与复用。
4. 脆弱性(Fragility):对代码一处的修改,导致了系统中其他看似无关部分功能的意外损坏。
5. 晦涩性(Obscurity):代码意图不明,结构混乱,导致阅读者难以理解其功能和设计。
6. 数据泥团(Data Clump): 多个数据项总是一起出现在不同方法的参数中,暗示着它们应该被组合成一个独立的对象。
7. 不必要的复杂性(Needless Complexity):用“杀牛刀” 去解决“杀鸡”的问题,过度设计使系统变得臃肿且难以理解。

- 【非常重要!!】无论是你自己编写代码,还是阅读或审核他人代码时,都要严格遵守上述硬性指标,以及时刻关注优雅的架构设计。
- 【非常重要!!】无论何时,一旦你识别出那些可能侵蚀我们代码质量的「坏味道」,都应当立即询问用户是否需要优化, 并给出合理的优化建议。
