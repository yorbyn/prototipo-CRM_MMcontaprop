// Interacciones puntuales (sin frameworks).
document.addEventListener("DOMContentLoaded", function () {
  // Confirmación antes de acciones destructivas: <form data-confirmar="¿Seguro?">
  document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
    });
  });

  // Formulario de propiedad: mostrar "modalidad de arriendo" solo si la operación es arriendo.
  var operacion = document.getElementById("id_operacion");
  var modalidad = document.getElementById("id_modalidad_arriendo");
  if (operacion && modalidad) {
    // Contenedor del campo que crea crispy-forms (etiqueta + campo + ayuda).
    var bloque = document.getElementById("div_id_modalidad_arriendo");
    var actualizar = function () {
      var esArriendo = operacion.value === "arriendo";
      if (bloque) bloque.style.display = esArriendo ? "" : "none";
      if (!esArriendo) modalidad.value = "";
    };
    operacion.addEventListener("change", actualizar);
    actualizar();
  }

  // Validación en el navegador (la validación definitiva siempre ocurre en el servidor).
  document.querySelectorAll("form.validar").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!form.checkValidity()) { e.preventDefault(); e.stopPropagation(); }
      form.classList.add("was-validated");
    });
  });
});
