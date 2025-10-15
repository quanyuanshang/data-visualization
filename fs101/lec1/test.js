const celsiusToFahrenheit = (temperature) => {
    return (temperature * 9/5) + 32;
} 
let temperatures = [1, 2, 7, 19];
for (let i = 0; i < temperatures.length; i++) {
    console.log(celsiusToFahrenheit(temperatures[i]));
}